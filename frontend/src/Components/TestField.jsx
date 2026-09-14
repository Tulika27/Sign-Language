import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';

function TestField({ image = "src\\assets\\isl.jpg", heading = "Basic Test", subHeading = "Test Your Learning", linkTo = "/test" ,lockTo=true}) {
  const [locked, setLocked] = useState(lockTo); // Lock state

  var someProperty='';

  // useEffect(()=>{
  //   setLocked('true');
  // }),[someProperty];

  return (
    <div className="relative flex flex-col rounded-lg shadow-2xl p-3 lg:w-80 w-70 justify-center">
      {/* Image Section */}
      <div className='h-60'>
        <img
          src={image}
          alt="Sign Test"
          className='w-full h-full object-contain'
          />
      </div>
      {/* Heading & Subheading */}
      <div className="p-4">
        <h2 className="text-xl text-blue-600 font-serif font-bold flex justify-center">{heading}</h2>
        <p className="text-gray-500 flex justify-center">{subHeading}</p>
      </div>

      {/* Start Button (Disabled if locked) */}
      <div className='w-full flex justify-center'>
        <Link to={locked ? "#" : linkTo} onClick={(e) => locked && e.preventDefault()}>
          <button 
            className={`mt-4 px-6 py-2 rounded hover:cursor-pointer ${locked ? "bg-blue-400 cursor-not-allowed" : "bg-blue-500 text-white hover:bg-blue-600"}`}
          >
            {locked ? "🔒" : "Start"}
          </button>
        </Link>
      </div>

      {/* Lock Overlay */}
      {locked && (
        <div className="absolute inset-0 bg-gray-200/50 rounded-lg flex justify-center items-center">
         
        </div>
      )}


    </div>
  );
}

export default TestField;
