// server.js
const express = require('express');
const mysql = require('mysql');
const bodyParser = require('body-parser');
const app = express();
const PORT = 3000;

app.use(bodyParser.json()); // Middleware to parse JSON data

// MySQL connection setup
const db = mysql.createConnection({
    host: 'localhost',
    user: 'root',
    password: 'Shambhavi', // Add your MySQL password here
    database: 'stock_management_system'
});

// Connect to MySQL
db.connect((err) => {
    if (err) throw err;
    console.log('Connected to MySQL Database!');
});

// Route to handle signup
app.post('/signup', (req, res) => {
    const { name, date_of_birth, mail_id, pan_id } = req.body;
    const insertUserQuery = `
        INSERT INTO User (name, date_of_birth, mail_id, pan_id)
        VALUES (?, ?, ?, ?)
    `;
    db.query(insertUserQuery, [name, date_of_birth, mail_id, pan_id], (err, result) => {
        if (err) {
            if (err.code === 'ER_DUP_ENTRY') {
                return res.status(400).json({ message: 'Email or PAN ID already exists' });
            }
            return res.status(500).json({ message: 'Database error', error: err });
        }
        res.status(201).json({ message: 'User registered successfully' });
    });
});

// Route to handle login
app.post('/login', (req, res) => {
    const { name, pan_id } = req.body;
    const loginQuery = `
        SELECT * FROM User WHERE name = ? AND pan_id = ?
    `;
    db.query(loginQuery, [name, pan_id], (err, results) => {
        if (err) return res.status(500).json({ message: 'Database error', error: err });

        if (results.length > 0) {
            // User authenticated
            res.status(200).json({ message: 'Login successful' });
        } else {
            res.status(401).json({ message: 'Invalid name or PAN ID' });
        }
    });
});

// Start the server
app.listen(PORT, () => {
    console.log(`Server is running on http://localhost:${PORT}`);
});
