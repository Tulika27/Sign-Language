require("dotenv").config();
const PORT = process.env.PORT || 5001;
const express = require("express");
const cors = require("cors");


require("./Models/db");

const authRoutes = require("./routes/authRoutes");
const testRoutes = require("./routes/testRoutes");
const certificateRoutes = require("./routes/certificateRoute");
// const courseRoutes = require("./routes/courseRoutes");
const ensureAuth = require("./Middleware/Auth");

const app = express();

app.use(express.json());
app.use(cors());

app.use("/auth", authRoutes);

app.use("/api", testRoutes);

app.use("/api", certificateRoutes);


// app.use("/course",ensureAuth, courseRoutes);

app.get("/hello", (req, res) => {
  res.send("World");
});

// app.post("/generate-certificate", async (req, res) => {
// });

app.listen(PORT, () => console.log(`Server running on port ${PORT}`));
