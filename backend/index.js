// backend/index.js
require('dotenv').config();
const express = require('express');
const session = require('express-session');
const cookieParser = require('cookie-parser');
const axios = require('axios');
const cors = require('cors');
const { GoogleGenerativeAI } = require('@google/generative-ai');
const fetch = require('node-fetch'); // Using node-fetch v2

const app = express();
const PORT = process.env.PORT || 3001;

// ========= FAKE IN-MEMORY DATABASE =========
const analysesDB = [];

// ========= MIDDLEWARE SETUP (FIXED) =========
// We only need one body parser. This will handle all JSON requests, including webhooks.
app.use(express.json()); // <-- SIMPLIFIED: This is the only body parser we need.

app.use(cors({
  origin: 'http://localhost:3000',
  credentials: true,
}));
app.use(cookieParser());
app.use(session({
  secret: process.env.SESSION_SECRET,
  resave: false,
  saveUninitialized: false,
  cookie: {
    httpOnly: true,
    secure: process.env.NODE_ENV === 'production',
    maxAge: 24 * 60 * 60 * 1000
  }
}));

// ========= GITHUB & AI SETUP =========
const GITHUB_CLIENT_ID = process.env.GITHUB_CLIENT_ID;
const GITHUB_CLIENT_SECRET = process.env.GITHUB_CLIENT_SECRET;
const GEMINI_API_KEY = process.env.GEMINI_API_KEY;

const genAI = new GoogleGenerativeAI(GEMINI_API_KEY);
const model = genAI.getGenerativeModel({ model: "gemini-1.5-flash"});

// ========= AUTHENTICATION ROUTES =========
app.get('/api/auth/github', (req, res) => {
  const githubAuthUrl = `https://github.com/login/oauth/authorize?client_id=${GITHUB_CLIENT_ID}&scope=read:user%20repo%20workflow`;
  res.redirect(githubAuthUrl);
});

app.get('/api/auth/github/callback', async (req, res) => {
  const { code } = req.query;
  try {
    const tokenResponse = await axios.post('https://github.com/login/oauth/access_token', { client_id: GITHUB_CLIENT_ID, client_secret: GITHUB_CLIENT_SECRET, code }, { headers: { 'Accept': 'application/json' }});
    const { access_token } = tokenResponse.data;
    if (access_token) {
      req.session.accessToken = access_token;
      const userResponse = await axios.get('https://api.github.com/user', { headers: { 'Authorization': `token ${access_token}` }});
      req.session.user = { id: userResponse.data.id, username: userResponse.data.login, avatar_url: userResponse.data.avatar_url };
      res.redirect('http://localhost:3000/dashboard');
    } else {
      res.status(400).send('Failed to obtain access token.');
    }
  } catch (error) {
    console.error('Error during GitHub OAuth callback:', error.response ? error.response.data : error.message);
    res.status(500).send('Authentication failed.');
  }
});

// ========= WEBHOOK HANDLER =========
app.post('/api/webhooks/github', async (req, res) => {
    // FIXED: The body is now already a JSON object thanks to express.json(), so we don't need to parse it.
    const event = req.body;
    console.log('Received webhook event:', event.action);

    if (event.workflow_run && event.action === 'completed' && event.workflow_run.conclusion === 'failure') {
        const workflowRun = event.workflow_run;
        const repoFullName = event.repository.full_name;
        
        console.log(`Processing failed workflow run ${workflowRun.id} for repo ${repoFullName}`);

        try {
            const placeholderToken = process.env.GITHUB_PERSONAL_ACCESS_TOKEN;
            if (!placeholderToken) {
              console.error("No Personal Access Token found in .env to process webhook.");
              return res.status(400).send("Cannot process webhook without authentication context.");
            }

            const jobsUrl = workflowRun.jobs_url;
            const jobsResponse = await axios.get(jobsUrl, {
                headers: { 'Authorization': `token ${placeholderToken}`, 'Accept': 'application/vnd.github.v3+json' }
            });
            const failedJob = jobsResponse.data.jobs.find(job => job.conclusion === 'failure');

            if (!failedJob) {
                console.log('No specific failed job found.');
                return res.status(200).send('No failed job to analyze.');
            }

            const logUrl = `https://api.github.com/repos/${repoFullName}/actions/jobs/${failedJob.id}/logs`;
            // GitHub API for logs redirects, so we need to handle that.
            const logRedirectResponse = await axios.get(logUrl, {
                headers: { 'Authorization': `token ${placeholderToken}`},
                maxRedirects: 0, // Stop axios from following the redirect automatically
                validateStatus: status => status === 302 // Expect a redirect
            }).catch(err => err.response); // Catch the 302 redirect as a "response"

            const actualLogUrl = logRedirectResponse.headers.location;
            const logTextResponse = await fetch(actualLogUrl);
            const logText = await logTextResponse.text();

            const prompt = `
                You are an expert software development assistant. Analyze the following CI/CD error log and provide a concise root cause and a suggested fix.
                Format your response as a JSON object with two keys: "conclusion" and "suggestion".

                Log:
                ---
                ${logText.substring(0, 30000)} 
                ---
            `;

            const result = await model.generateContent(prompt);
            const responseText = await result.response.text();
            const analysis = JSON.parse(responseText.replace(/```json|```/g, '').trim());

            console.log('AI Analysis:', analysis);

            const newAnalysis = {
                id: analysesDB.length + 1,
                repoId: event.repository.id,
                repoFullName: event.repository.full_name,
                githubRunId: workflowRun.id,
                status: workflowRun.conclusion,
                conclusion: analysis.conclusion,
                suggestion: analysis.suggestion,
                rawLog: logText.substring(0, 30000),
                createdAt: new Date().toISOString(),
            };
            analysesDB.push(newAnalysis);
            console.log(`SUCCESS: Saved analysis for run ${workflowRun.id} to in-memory DB.`);

        } catch (error) {
            console.error('Error processing webhook:', error.response ? error.response.data : error.message);
        }
    }

    res.status(200).send('Webhook received.');
});


// ========= PROTECTED API ROUTES =========
const isAuthenticated = (req, res, next) => {
  if (req.session.user) { next(); } else { res.status(401).json({ message: 'Unauthorized' }); }
};

app.get('/api/user', isAuthenticated, (req, res) => {
  res.json(req.session.user);
});

app.get('/api/repos', isAuthenticated, async (req, res) => {
    try {
        const reposResponse = await axios.get('https://api.github.com/user/repos?sort=updated&per_page=100', { headers: { 'Authorization': `token ${req.session.accessToken}` }});
        res.json(reposResponse.data);
    } catch (error) {
        console.error('Error fetching repositories:', error.message);
        res.status(500).send('Failed to fetch repositories.');
    }
});

app.get('/api/analyses/:repoId', isAuthenticated, (req, res) => {
    const { repoId } = req.params;
    const repoAnalyses = analysesDB.filter(analysis => analysis.repoId == parseInt(repoId));
    res.json(repoAnalyses);
});


app.listen(PORT, () => {
  console.log(`Backend server listening on http://localhost:${PORT}`);
});
