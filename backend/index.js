// backend/index.js
require('dotenv').config();
const express = require('express');

const app = express();
const PORT = process.env.PORT || 3001; // Use 3001 for the backend

// Middleware to parse JSON bodies
app.use(express.json());

// A simple test route to make sure the server is working
app.get('/api/health', (req, res) => {
  res.json({ status: 'ok', message: 'Backend is running!' });
});

app.listen(PORT, () => {
  console.log(`Backend server listening on http://localhost:${PORT}`);
});
