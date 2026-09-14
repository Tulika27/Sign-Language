const mongoose = require('mongoose');

// Define the test schema
const testSchema = new mongoose.Schema({
    userId: { type: mongoose.Schema.Types.ObjectId, ref: 'User' },  // Reference to User
    user:String,
    category: String,
    score: Number,
    correct_signs: Number,
    total_signs: Number,
    certificate_url: String,
    date: { type: Date, default: Date.now },
});

// Create a Test model from the schema
const Test = mongoose.model('Test', testSchema);
module.exports=Test;