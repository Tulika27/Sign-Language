import React from 'react';
import { useNavigate } from 'react-router-dom';
import NewNavbar from './NewNavbar'
import { useState,useEffect,useContext } from 'react';
import UserContext from '../Context/UserContext';


const passingScore=60;

const Result = ({category,totalSign}) => {
  const [user,setUser]=useState('');
  const [userId,setUserId]=useState('');
  const [score,setScore]=useState(0);
  const {correct}=useContext(UserContext);


  
  useEffect(() => {
    setUser(localStorage.getItem('userName') || '');
    setUserId(localStorage.getItem('userId') || '');
    setScore(Math.floor(correct/totalSign*100));
}, []);


 
  const renderStars = (score) => {
    const fullStars = Math.floor((score / 100) * 5); // Full stars
    const halfStar = (score / 100) * 5 - fullStars >= 0.5; // Check if there is a half star
    const totalStars = 5;
  
    return Array.from({ length: totalStars }, (_, index) => {
      if (index < fullStars) {
        return (
          <span
            key={index}
            className={`text-5xl transition-transform transform ${"text-yellow-500  animate-pulse-star"}`}
            >
            🌟
          </span>
        );
      } else if (index === fullStars && halfStar) {
        return (
          <span
          key={index}
          className={`text-5xl transition-transform transform ${"text-yellow-300"}`}
          >
              ★  {/* Half star symbol */}
          </span>
        );
      } else {
        return (
          <span
            key={index}
            className={`text-5xl transition-transform transform ${"text-blue-100"}`}
          >
            ★ {/* Empty star symbol */}
          </span>
        );
      }
    });
  };

  const feedback=(score)=>{
    if(score<60 && score>55){
      return(
        <>
        <div className='text-xl font-extrabold text-amber-800 animation-bounce'>
           Nice Try!!
        </div>
        </>
      )
    }else if(score>=60 && score<=75){
      return(
        <>
         <div className='text-xl font-extrabold text-amber-800 transition-shadow'>
           Great Job!!
        </div>
        </>
      )
    }else if(score>75){
      return(
        <>
        <div className='text-xl font-extrabold text-amber-800'>
           Excellent Job!!
        </div>
        </>
      )
    }

  }
  const navigate = useNavigate();

  const goBack = () => {
    navigate(-1);
  };

//downloadCertificate
  const downloadCertificate = async () => {
    const res = await fetch('http://localhost:5001/api/download', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name: user,
        course: `${categoryName} SIGN TEST `,
      }),
    });
  
    const blob = await res.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `certificate.pdf`;
    a.click();
    window.URL.revokeObjectURL(url);
  };

  return (
    <>
    <NewNavbar/>
    <div className="bg-blue-200 h-screen result-container p-6 text-center">
      <div className='bg-blue-400 p-15 rounded-2xl flex flex-col items-center'>

      <h2 className="text-4xl font-bold mb-4 text-blue-800">{category} Test Result</h2>
      <div className="stars my-4">
        {renderStars(score)}
        {feedback(score)}
      </div>
      <div className='bg-blue-800 p-10 font-semibold text-amber-100 rounded-2xl'>
      <p className="text-lg mb-4">{user} You completed the <span className="font-semibold">{category}</span> Test !!</p>
      <div className='font-bold text-xl text-green-400'>
      <p>Your Score: <span className="font-bold ">{score}%</span></p>
      </div>
      <p>Matched Signs: {correct}/{totalSign}</p>
      {/* Show feedback based on score */}
      {score >= passingScore ? (
        <div className="success mt-4">
          <p className="text-green-300 font-semibold">🎉 Congratulations! You passed!</p>
          <button
            className="bg-blue-500 text-white px-4 py-2 rounded-lg mt-2 inline-block cursor-pointer hover:bg-blue-400"
            onClick={downloadCertificate}
            >
            Download Certificate
          </button>
        </div>
      ) : (
        <div className="failure mt-4">
          <p className="text-red-400 font-semibold">❌ Sorry, you didn't pass this time.</p>
          <br />
          <p className='font-light '>You need at least {passingScore}% to pass.</p>
          <p> Don't worry, try again!</p>
          <button
            onClick={()=>setTimeout(goBack,500)} 
            className="bg-yellow-500 text-white hover:bg-green-500 px-4 py-2 rounded-lg mt-2 inline-block cursor-pointer"
            >
            Retake Test
          </button>
        </div>
      )}
      </div>
      <button
            onClick={() => navigate('/test')} 
            className="bg-amber-400 text-blue-900 hover:bg-green-400 px-4 py-2 rounded-lg mt-2 inline-block font-bold cursor-pointer"
            >
            Explore More Test
      </button>

      
      </div>
    </div>
  </>
  );
};
export default Result;
