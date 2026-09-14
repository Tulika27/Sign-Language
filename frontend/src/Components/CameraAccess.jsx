import React, { useRef, useEffect, useState } from "react";
import Webcam from "react-webcam";
import { Hands } from "@mediapipe/hands";
import * as cam from "@mediapipe/camera_utils";
import NewNavbar from "./NewNavbar";
import Buttons from "./Buttons";
import { useNavigate,Link } from "react-router-dom";

const CameraAccess = ({testName="Basic Sign Language Test"}) => {
  const webcamRef = useRef(null);
  const canvasRef = useRef(null);
  const [cameraOn, setCameraOn] = useState(false);
  let camera = null;

  const navigate=useNavigate();
  useEffect(() => {
    if (cameraOn) {
      startCamera();
    } else {
      stopCamera();
    }
  }, [cameraOn]);

  const startCamera = () => {
    if (webcamRef.current) {
      const hands = new Hands({
        locateFile: (file) => `https://cdn.jsdelivr.net/npm/@mediapipe/hands/${file}`,
      });

      hands.setOptions({
        maxNumHands: 1,
        modelComplexity: 1,
        minDetectionConfidence: 0.5,
        minTrackingConfidence: 0.5,
      });

      hands.onResults((results) => {
        drawHand(results);
      });

      camera = new cam.Camera(webcamRef.current.video, {
        onFrame: async () => {
          await hands.send({ image: webcamRef.current.video });
        },
        width: 640,
        height: 480,
      });

      camera.start();
    }
  };

  const stopCamera = () => {
    if (camera) {
      camera.stop();
    }
  };

  const drawHand = (results) => {
    const ctx = canvasRef.current.getContext("2d");
    ctx.clearRect(0, 0, canvasRef.current.width, canvasRef.current.height);

    if (results.multiHandLandmarks) {
      results.multiHandLandmarks.forEach((landmarks) => {
        landmarks.forEach((point) => {
          ctx.beginPath();
          ctx.arc(point.x * canvasRef.current.width, point.y * canvasRef.current.height, 5, 0, 2 * Math.PI);
          ctx.fillStyle = "blue";
          ctx.fill();
        });
      });
    }
  };

  return (
    <>
    <NewNavbar element={<Buttons name='Log Out'/>}/>
    <div className="bg-gray-900 h-screen w-screen">

    <div className="bg-gray-900 text-white w-screen">
      <Link to="/test">
      <div className="flex justify-start p-5">
        <Buttons name='Back'/>
      </div>
      </Link>
   
      <div className="justify-center  flex flex-col items-center">
      <h1 className="text-2xl font-bold mb-4">{testName}</h1>
      <div className="relative">
        {cameraOn && (
          <>
            <Webcam ref={webcamRef} className="rounded-lg shadow-lg w-[640px] h-[480px]" />
            <canvas ref={canvasRef} className="absolute top-0 left-0 w-[640px] h-[480px]" />
          </>
        )}
      </div>
      <div className="mt-4">
        <button
          onClick={() => setCameraOn(true)}
          className="bg-green-500 hover:bg-green-600 text-white font-bold py-2 px-4 rounded mr-2"
        >
          Start Camera
        </button>
        <button
          onClick={() => setCameraOn(false)}
          className="bg-red-500 hover:bg-red-600 text-white font-bold py-2 px-4 rounded"
          >
          Stop Camera
        </button>
      </div>
      <Link to='/download'> 
        <div className='p-20'>
        <Buttons name="Download Certificate"/>
      </div>
      </Link>
      </div>
    </div>
    </div>
    </>
  );
};

export default CameraAccess;