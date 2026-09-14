import React from 'react';

function TestHistory({user="UserName",category="TestName",score=0,correct=0,totalSign=0,date="Date"}) {
  
  
  const passingScore=60;
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
            className={`text-5xl transition-transform transform ${"text-gray-300"}`}
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
        
        <div className='text-xl font-extrabold text-amber-800 animation-bounce text-center'>
           It was Nice Try!!
        </div>
        </>
      )
    }else if(score>=60 && score<=75){
      return(
        <>
         <div className='text-xl font-extrabold text-amber-800 transition-shadow text-center'>
           It was Great !!
        </div>
        </>
      )
    }else if(score>75){
      return(
        <>
        <div className='text-xl font-extrabold text-amber-800 text-center'>
           It was Excellent !!
        </div>
        </>
      )
    }

  }

  return (
    <>
    <div>
      <div className='p-5 rounded-2xl flex flex-col items-center w-96 
      shadow-2xl'>

      <h2 className="text-2xl font-bold p-2 text-amber-900">{category} Test Result</h2>
      <div className="stars my-2">
        {renderStars(score)}
        {feedback(score)}
      </div>

      <div className=' p-5 font-semibold text-gray-500 rounded-2xl text-center text-2xl'>
      {/* <p className="text-lg mb-4">{user} You have completed the <span className="font-semibold">{category}</span> Test </p> */}
      <div className='font-bold text-xl'>
      <p>Your Score: <span className="font-bold ">{score}%</span></p>
      Matched : {correct}/{totalSign}
      </div>
      {/* Show feedback based on score */}
      {score >= passingScore ? (
        <div className="success mt-4">
          <p className="text-green-600 font-semibold">🎉 Passed!🎉 </p>
          <a
            className="bg-blue-500 text-amber-50 px-4 py-2 rounded-lg mt-2 inline-block cursor-pointer hover:bg-blue-800
            text-sm"
            download
            >
            Download Certificate
          </a>
        </div>
      ) : (
        <div className="failure mt-4">
          <p className="text-red-400 font-semibold">❌ Failed</p>
          <br />
        </div>
      )}
      </div>
     
      Date: {date}

      
      </div>
    </div>
    </>
    
  )
}

export default TestHistory
