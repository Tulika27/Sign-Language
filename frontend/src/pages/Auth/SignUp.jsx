import React, { useState } from "react";
import { Link } from "react-router-dom";
import { handleError } from "../../Components/Toast";
import { handleSuccess } from "../../Components/Toast";
import axios from "axios";
import { useNavigate } from "react-router-dom";
import Navbar from "../../Components/Navbar";
import offEye from "../../assets/offEye.png";
import onEye from "../../assets/onEye.png";

const SignUp = () => {
  const [formData, setFormData] = useState({
    name: "",
    email: "",
    password: "",
  });

  const [showPassword, setShowPassword] = useState(false);
  const navigate = useNavigate();

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    const { name, email, password } = formData;
    if (!name || !email || !password) {
      return handleError("Enter Valid Data!!");
    }
    try {
      const url = "http://localhost:5001/auth/signup";
      const response = await fetch(url,
        {
          method: "POST",
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(formData)
        }
      );

      const result = await response.json();

     if (response.status === 201) {
      handleSuccess("Signup successful!");
      setTimeout(() => navigate("/login"), 1000);
    } 
    else if (response.status === 409) { 
      // User already exists
      handleError("User already registered! Redirecting to login...");
      setTimeout(() => navigate("/login"), 1000);
    } 
    else {
      handleError(result.message || "Signup failed! Please try again.");
    }
  } catch (error) {
    console.error("Signup Error:", error);
    handleError("Something went wrong! Try again later.");
  }
  };

  return (
    <>
      <nav className=" top-0 z-50">
        <Navbar />
      </nav>
      <div className="flex items-center justify-center min-h-screen bg-gray-100">
        <div className="bg-white p-6 rounded-lg shadow-lg w-96">
          <h2 className="text-2xl font-bold text-center mb-4">Sign Up</h2>
          <form onSubmit={handleSubmit}>
            <div className="mb-4">
              <label className="block text-gray-700">Name</label>
              <input
                type="text"
                name="name"
                value={formData.name}
                onChange={handleChange}
                className="w-full p-2 border rounded-lg mt-1 focus:outline-none focus:ring-2 focus:ring-blue-400"
              />
            </div>
            <div className="mb-4">
              <label className="block text-gray-700">Email</label>
              <input
                type="email"
                name="email"
                value={formData.email}
                onChange={handleChange}
                className="w-full p-2 border rounded-lg mt-1 focus:outline-none focus:ring-2 focus:ring-blue-400"
                required
              />
            </div>

            <div className="mb-4 relative"> {/* ✅ Added relative wrapper */}
              <label className="block text-gray-700">Password</label>
              <input
                type={showPassword ? "text" : "password"} // ✅ Dynamic Type
                name="password"
                value={formData.password}
                onChange={handleChange}
                className="w-full p-2 border rounded-lg mt-1 focus:outline-none focus:ring-2 focus:ring-blue-400"
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 top-9 text-gray-600 hover:text-gray-900"
              >
                <img
                  src={showPassword ? offEye : onEye}
                  alt="Toggle Password Visibility"
                  className="w-6 h-6"
                />
              </button>
            </div>
            <button
              type="submit"
              className="w-full bg-blue-500 text-white p-2 rounded-lg hover:bg-blue-600 transition"
            >
              Sign Up
            </button>
          </form>
          <span >Already have an Account </span>
          <Link className="text-blue-800 font-bold" to="/login">Login</Link>
        </div>
      </div>
    </>
  );
};

export default SignUp;
