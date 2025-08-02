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

// ========= MIDDLEWARE SETUP =========
// Use express.raw({type: 'application/json'}) for webhooks to verify signatures later
// For now, we use express.json() for simplicity.
app.use('/api/webhooks/github', express.raw({ type: 'application/json' }));
app.use(express.json());

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

// ========= AUTHENTICATION ROUTES (Unchanged) =========
app.get('/api/auth/github', (req, res) => {
  const githubAuthUrl = `https://github.com/login/oauth/authorize?client_id=${GITHUB_CLIENT_ID}&scope=read:user%20repo%20admin:repo_hook`;
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
      // TODO: Save user to database here
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
    // For now, we assume the webhook is valid. In production, you'd verify the signature.
    const event = JSON.parse(req.body);
    console.log('Received webhook event:', event.action);

    // We only care about completed workflow runs that have failed
    if (event.workflow_run && event.action === 'completed' && event.workflow_run.conclusion === 'failure') {
        const workflowRun = event.workflow_run;
        const repoFullName = event.repository.full_name;
        const [owner, repo] = repoFullName.split('/');

        console.log(`Processing failed workflow run ${workflowRun.id} for repo ${repoFullName}`);

        try {
            // TODO: We need a way to get the installation's access token to act on its behalf.
            // For now, we will use a placeholder token. In a real app, you'd get this from your app's installation logic.
            const placeholderToken = req.session.accessToken || process.env.GITHUB_PERSONAL_ACCESS_TOKEN;
            if (!placeholderToken) {
              console.error("No access token available to process webhook.");
              return res.status(400).send("Cannot process webhook without authentication context.");
            }

            // 1. Get the jobs for the failed workflow run
            const jobsUrl = workflowRun.jobs_url;
            const jobsResponse = await axios.get(jobsUrl, {
                headers: { 'Authorization': `token ${placeholderToken}`, 'Accept': 'application/vnd.github.v3+json' }
            });
            const failedJob = jobsResponse.data.jobs.find(job => job.conclusion === 'failure');

            if (!failedJob) {
                console.log('No specific failed job found.');
                return res.status(200).send('No failed job to analyze.');
            }

            // 2. Get the log for the failed job
            const logUrl = `https://api.github.com/repos/${repoFullName}/actions/jobs/${failedJob.id}/logs`;
            const logResponse = await axios.get(logUrl, {
                headers: { 'Authorization': `token ${placeholderToken}`, 'Accept': 'application/vnd.github.v3+json' },
                responseType: 'stream' // We get the redirect URL first
            });

            const actualLogUrl = logResponse.request.res.responseUrl;
            const logTextResponse = await fetch(actualLogUrl);
            const logText = await logTextResponse.text();

            // 3. Analyze the log with Gemini
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

            // 4. TODO: Save the analysis to your database
            // Example: db.query('INSERT INTO analyses (repo_id, github_run_id, status, conclusion, suggestion) VALUES (...)', [...]);
            console.log(`SAVING to DB: repo: ${event.repository.id}, run: ${workflowRun.id}, conclusion: ${analysis.conclusion}`);

        } catch (error) {
            console.error('Error processing webhook:', error.response ? error.response.data : error.message);
        }
    }

    res.status(200).send('Webhook received.');
});


// ========= PROTECTED API ROUTES (Unchanged) =========
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

// TODO: Add a new route to fetch analyses from the database
// app.get('/api/analyses', isAuthenticated, async (req, res) => { ... });

app.listen(PORT, () => {
  console.log(`Backend server listening on http://localhost:${PORT}`);
});
