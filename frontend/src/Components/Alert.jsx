import React from 'react'
import { Link } from 'react-router-dom'

function Alert({message="Welcome Back!!" , onClose}) {
  return (
    <>
     <div className="fixed inset-0 flex items-center justify-center bg-blue-900 bg-opacity-50 z-50">
      <div className="bg-stone-100 rounded-lg shadow-lg text-center p-10">
        <h2 className="text-2xl font-bold font-sans text-green-600">🎉 {message} 🎉</h2>
        <br />
       
        <br/>
        <button
          className="mt-4 bg-blue-500 text-stone-100 font-bold font-sans px-4 py-2 rounded-lg shadow-md hover:bg-blue-600 transition"
          onClick={onClose}
        >
          Try Next ➜
        </button>
      </div>
    </div>

    </>
    
  )
}

export default Alert
