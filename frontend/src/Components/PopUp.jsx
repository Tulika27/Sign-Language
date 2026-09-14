const PopUp = ({ label, confidence, onClose }) => {
  return (
    <div className="fixed inset-0 flex items-center justify-center bg-blue-900 bg-opacity-50 z-50">
      <div className="bg-stone-100 rounded-lg shadow-lg text-center p-10">
        <h2 className="text-2xl font-bold font-sans text-green-600">🎉 Correct! 🎉</h2>
        <br />
        <p className="text-lg mt-2 font-bold text-gray-500">
        {/* <span className="text-2xl text-blue-500 font-bold">{confidence}% </span> */}
          Sign Matched With Letter <span className=" text-2xl font-bold font-sans text-blue-500">"{label}" </span> 
          
        </p>
        <br/>
        <button
          className="mt-4 bg-blue-500 text-stone-100 font-bold font-sans px-4 py-2 rounded-lg shadow-md hover:bg-blue-600 transition"
          onClick={onClose}
        >
          Try Next ➜
        </button>
      </div>
    </div>
  );
};

export default PopUp;
