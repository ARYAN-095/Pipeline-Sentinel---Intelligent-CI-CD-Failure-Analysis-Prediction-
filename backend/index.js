// backend/index.js
require('dotenv').config();
const express = require('express');
const session = require('express-session');
const cookieParser = require('cookie-parser');
const axios = require('axios');
const cors = require('cors');

const app = express();
const PORT = process.env.PORT || 3001;

// ========= MIDDLEWARE SETUP =========
app.use(cors({
  origin: 'http://localhost:3000', // Allow requests from our frontend
  credentials: true, // Allow cookies to be sent
}));
app.use(cookieParser());
app.use(express.json());
app.use(session({
  secret: process.env.SESSION_SECRET,
  resave: false,
  saveUninitialized: false,
  cookie: {
    httpOnly: true,
    secure: process.env.NODE_ENV === 'production', // Use secure cookies in production
    maxAge: 24 * 60 * 60 * 1000 // 24 hours
  }
}));

// ========= GITHUB OAUTH CONSTANTS =========
const GITHUB_CLIENT_ID = process.env.GITHUB_CLIENT_ID;
const GITHUB_CLIENT_SECRET = process.env.GITHUB_CLIENT_SECRET;

// ========= AUTHENTICATION ROUTES =========

// 1. Redirects user to GitHub's authorization page
app.get('/api/auth/github', (req, res) => {
  const githubAuthUrl = `https://github.com/login/oauth/authorize?client_id=${GITHUB_CLIENT_ID}&scope=read:user%20repo`;
  res.redirect(githubAuthUrl);
});

// 2. GitHub redirects back to this URL after authorization
app.get('/api/auth/github/callback', async (req, res) => {
  const { code } = req.query;

  try {
    // Exchange the authorization code for an access token
    const tokenResponse = await axios.post('https://github.com/login/oauth/access_token', {
      client_id: GITHUB_CLIENT_ID,
      client_secret: GITHUB_CLIENT_SECRET,
      code,
    }, {
      headers: { 'Accept': 'application/json' }
    });

    const { access_token } = tokenResponse.data;

    if (access_token) {
      // Store the access token in the session
      req.session.accessToken = access_token;

      // Fetch the user's profile from GitHub
      const userResponse = await axios.get('https://api.github.com/user', {
        headers: { 'Authorization': `token ${access_token}` }
      });
      
      // Store user info in the session
      req.session.user = {
        id: userResponse.data.id,
        username: userResponse.data.login,
        avatar_url: userResponse.data.avatar_url
      };

      // Redirect user to the frontend dashboard
      res.redirect('http://localhost:3000/dashboard');
    } else {
      res.status(400).send('Failed to obtain access token.');
    }
  } catch (error) {
    console.error('Error during GitHub OAuth callback:', error.response ? error.response.data : error.message);
    res.status(500).send('Authentication failed.');
  }
});

// ========= PROTECTED API ROUTES =========

// Middleware to check if user is authenticated
const isAuthenticated = (req, res, next) => {
  if (req.session.user) {
    next();
  } else {
    res.status(401).json({ message: 'Unauthorized' });
  }
};

// Returns the logged-in user's data
app.get('/api/user', isAuthenticated, (req, res) => {
  res.json(req.session.user);
});

// Fetches repositories for the logged-in user
app.get('/api/repos', isAuthenticated, async (req, res) => {
    try {
        const reposResponse = await axios.get('https://api.github.com/user/repos?sort=updated&per_page=100', {
            headers: { 'Authorization': `token ${req.session.accessToken}` }
        });
        res.json(reposResponse.data);
    } catch (error) {
        console.error('Error fetching repositories:', error.message);
        res.status(500).send('Failed to fetch repositories.');
    }
});

app.listen(PORT, () => {
  console.log(`Backend server listening on http://localhost:${PORT}`);
});
