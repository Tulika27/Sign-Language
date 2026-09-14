import React from 'react'
import { useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { toast } from 'react-toastify';

function ResetPassword() {
  const { token } = useParams(); // token from URL
  const [newPassword, setNewPassword] = useState("");
  

  const navigate=useNavigate();
  const handleReset = async (e) => {
    e.preventDefault();
    try{
    const res = await fetch("http://localhost:5001/auth/reset-password", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ token, newPassword }),
    });

    const data = await res.json();
    
    if (res.ok) {
          toast.success(data.message || "Password Reset Succesfully!!");
          navigate("/login");
          
        } else {
          toast.error(data.message || "Something went wrong");
        }
      } catch (err) {
        toast.error("Server error");
      }
        
      };

  
  return (
    <>
    <div className='bg-gray-100 h-screen pt-20'>
    <div className="p-5 max-w-md mx-auto flex flex-col items-center bg-white rounded-2xl shadow">
      <h2 className="text-2xl font-bold mb-4 text-cyan-800">Reset Password</h2>
      <form onSubmit={handleReset} className="space-y-3 flex flex-col">
        <input
          type="password"
          placeholder="Enter new password"
          className="w-sm p-2 border rounded "
          value={newPassword}
          onChange={(e) => setNewPassword(e.target.value)}
          />
          <div className='text-cyan-800 font-semibold cursor-pointer hover:text-cyan-900 ' onClick={()=>navigate('/forgot-password')}>Resend Link</div>
        <button className="bg-green-500 text-white px-4 py-2 rounded font-semibold">Reset Password</button>
      </form>
        </div>
    </div>
    </>
    
  )
}

export default ResetPassword
