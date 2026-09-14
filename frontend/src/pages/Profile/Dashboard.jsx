import React, { useEffect, useState } from 'react'
import TestHistory from '../../Components/TestHistory'
import NewNavbar from '../../Components/NewNavbar'
import Footer from '../../Components/Footer'
import axios from 'axios';



function Dashboard() {

  const [testInfo, setTestInfo] = useState([]);
  const userId = localStorage.getItem('userId');
  const sortedTests = testInfo.sort((a, b) => new Date(b.date) - new Date(a.date));

  const fetchInfo = async () => {
    try {
      const response = await axios.post('http://localhost:5001/api/getInfo', {
        userId: userId
      })
      console.log(response.data);
      setTestInfo(response.data);

    } catch (err) {
      console.log("Error:", err);
    }
  };

  const deleteData = async () => {
    try {
      console.log("active deletion!")
      const confirm = window.confirm("Are you sure you want to delete your test history?");
      if (!confirm) return;

      const response = axios.post('http://localhost:5001/api/deleteHistory', {
        userId: userId
      });
      fetchInfo();
      if (response.status === 200) {
        toast.success("Test history deleted successfully");
      }

    } catch (err) {
      console.log("Error", err);
    }
  }
  useEffect(() => {
    console.log("useEffect triggered");
    fetchInfo();
  }, []);



  return (
    <>
      <NewNavbar />
      <div className=''>
      <div className='text-center text-3xl p-5 font-bold text-blue-500'>History</div>
      <div className='flex flex-wrap flex-col gap-10'>

        {testInfo.length === 0 ? (
          <div className="text-center text-gray-500 ">No test history found.</div>
        ) : (
          <>
            <div className='flex flex-wrap justify-center gap-10'>
              {sortedTests.map((test, index) => (
                <TestHistory
                key={index}
                user={test.user}
                category={test.category}
                correct={test.correct_signs}
                totalSign={test.total_signs}
                score={test.score}
                date={new Date(test.date).toLocaleDateString()}
                certificate={test.certificate_url}
                />
              ))}
            </div>

            <div className='flex justify-center'>
            <button className='bg-red-500 p-4 font-medium rounded-2xl text-white hover:bg-red-600 
            cursor-pointer
            '
            onClick={() => deleteData()}>
              Delete History
            </button>
            </div>
          </>
)
}
      </div>
    </div>
      <Footer />
    </>

  )
}

export default Dashboard
