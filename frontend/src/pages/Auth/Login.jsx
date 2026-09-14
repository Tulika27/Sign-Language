import React, { useState } from "react";
import { Link ,useNavigate} from "react-router-dom";
import { ToastContainer } from "react-toastify";
import { handleError, handleSuccess } from "../../Components/Toast";
import Navbar from "../../Components/Navbar";
import offEye from "../../assets/offEye.png";
import onEye from "../../assets/onEye.png";

const Login = () => {
  const [formData, setFormData] = useState({
    email: "",
    password: "",
  });

  const navigate=useNavigate();
  const [showPassword, setShowPassword] = useState(false);

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    const {email,password}=formData;
        if(!email){
          return handleError("Enter Email !!");
        }else if(!password){
          return handleError('Enter Password!!');
        }
        try {
          const url="http://localhost:5001/auth/login";
          const response=await fetch(url,
            {
              method:"POST",
              headers:{'Content-Type':'application/json'},
              body:JSON.stringify(formData)
            }
          )
        
          const result=await response.json();

          const {message,jwtToken,success,userName,error,userId}=result;

          if(success){
            handleSuccess(message);
            localStorage.setItem('token',jwtToken);
            localStorage.setItem('userName',userName);
            localStorage.setItem('userId',userId);

            setTimeout(()=>{
              navigate('/home');
            },500)
          }else if(error){
            const detail=error?.details[0].message;
            handleError(detail);
          }else{
            handleError(message);
          }
          console.log(result);
        } catch (error) {
          console.log(error);
        }
  };
  

  return (
    <>
    <nav className=" top-0 z-50">
            <Navbar/>
      </nav>
    <div
    style={{backgroundImage:`url('/src/assets/home')`}}
    className=" flex items-center justify-center min-h-screen bg-gray-100">
      <div className="bg-white p-6 rounded-lg shadow-lg w-96">
        <h2 className="text-2xl font-bold text-center mb-4">Login</h2>
        <form onSubmit={handleSubmit}>
          <div className="mb-4">
            <label className="block text-gray-700">Email</label>
            <input
              type="email"
              name="email"
              value={formData.email}
              onChange={handleChange}
              className="w-full p-2 border rounded-lg mt-1 focus:outline-none focus:ring-2 focus:ring-blue-400"
              // required
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
            <Link to="/forgot-password" className="text-blue-600 font-semibold text-sm ">Forgot Password</Link>
          <button
            type="submit"
            className="w-full bg-blue-500 text-white p-2 rounded-lg hover:bg-blue-600 transition
            hover:cursor-pointer"
          >
            Login
          </button>
        </form>
        <div className="mt-3 font-bold text-blue-800">
          <Link to="/signup">Click for Signup</Link>
        </div>
      </div>
    </div>
    
    </>
  );
};

export default Login;
