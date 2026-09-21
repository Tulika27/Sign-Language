import { useEffect, useRef, useState, useContext } from "react";
import { useNavigate } from "react-router-dom";
import { Hands } from "@mediapipe/hands";
import * as cameraUtils from "@mediapipe/camera_utils";
import UserContext from "../../Context/UserContext";

const BASE_URL = "http://localhost:4996";
const TEST_LENGTH = 5;
const MAX_CAPTURE_FRAMES = 90;
const MIN_CAPTURE_FRAMES = 8;
const SCORE_API_URL = "http://localhost:5001/api/create";

const chooseWords = (labels) => {
  const shuffled = [...labels].sort(() => Math.random() - 0.5);
  return shuffled.slice(0, TEST_LENGTH);
};

function WordTest() {
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const overlayCanvasRef = useRef(null);
  const streamRef = useRef(null);
  const handsRef = useRef(null);
  const handCameraRef = useRef(null);
  const captureTimerRef = useRef(null);
  const framesRef = useRef([]);
  const { correct, setCorrect } = useContext(UserContext);
  const navigate = useNavigate();

  const [targetWords, setTargetWords] = useState([]);
  const [questionResults, setQuestionResults] = useState([]);
  const [currentQuestion, setCurrentQuestion] = useState(0);
  const [attempts, setAttempts] = useState(0);
  const [prediction, setPrediction] = useState(null);
  const [isCameraOn, setIsCameraOn] = useState(false);
  const [isCapturing, setIsCapturing] = useState(false);
  const [message, setMessage] = useState("Start the camera to begin.");

  const targetWord = targetWords[currentQuestion] || "";
  const testFinished = targetWords.length > 0 && currentQuestion >= targetWords.length;

  useEffect(() => {
    fetch(`${BASE_URL}/labels`)
      .then((response) => response.json())
      .then((data) => {
        const validLabels = data.labels || [];
        setTargetWords(chooseWords(validLabels));
        setQuestionResults(new Array(TEST_LENGTH).fill(null));
        setCorrect(0);
      })
      .catch(() => setMessage("Unable to load INCLUDE words."));

    return () => stopCamera();
  }, [setCorrect]);

  const stopCamera = () => {
    clearInterval(captureTimerRef.current);
    captureTimerRef.current = null;
    handCameraRef.current?.stop();
    handCameraRef.current = null;
    handsRef.current?.close();
    handsRef.current = null;
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
    if (videoRef.current) videoRef.current.srcObject = null;
    if (overlayCanvasRef.current) {
      overlayCanvasRef.current.getContext("2d").clearRect(
        0,
        0,
        overlayCanvasRef.current.width,
        overlayCanvasRef.current.height,
      );
    }
    setIsCameraOn(false);
    setIsCapturing(false);
  };

  const drawLiveHands = (results) => {
    const canvas = overlayCanvasRef.current;
    if (!canvas) return;
    const context = canvas.getContext("2d");
    context.clearRect(0, 0, canvas.width, canvas.height);
    context.strokeStyle = "#e190fc";
    context.fillStyle = "#A305d8";
    context.lineWidth = 4;
    context.font = "bold 22px Serif";

    results.multiHandLandmarks?.forEach((landmarks) => {
      const points = landmarks.map((point) => ({
        x: point.x * canvas.width,
        y: point.y * canvas.height,
      }));
      points.forEach((point) => {
        context.beginPath();
        context.arc(point.x, point.y, 4, 0, 2 * Math.PI);
        context.fill();
      });
      const xValues = points.map((point) => point.x);
      const yValues = points.map((point) => point.y);
      const xMin = Math.min(...xValues);
      const xMax = Math.max(...xValues);
      const yMin = Math.min(...yValues);
      const yMax = Math.max(...yValues);
      context.strokeRect(xMin, yMin, xMax - xMin, yMax - yMin);
      context.fillText("Hand", xMin + 5, Math.max(yMin - 8, 22));
    });
  };

  const captureFrame = () => {
    const video = videoRef.current;
    const canvas = canvasRef.current;
    if (!video || !canvas || video.readyState < 2 || framesRef.current.length >= MAX_CAPTURE_FRAMES) return;
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    canvas.getContext("2d").drawImage(video, 0, 0, canvas.width, canvas.height);
    canvas.toBlob((blob) => {
      if (blob) framesRef.current.push(blob);
    }, "image/jpeg", 0.85);
  };

  const startCamera = async () => {
    if (testFinished || !targetWord) return;
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: true });
      streamRef.current = stream;
      videoRef.current.srcObject = stream;
      const hands = new Hands({
        locateFile: (file) => `https://cdn.jsdelivr.net/npm/@mediapipe/hands/${file}`,
      });
      hands.setOptions({
        maxNumHands: 2,
        modelComplexity: 1,
        minDetectionConfidence: 0.5,
        minTrackingConfidence: 0.5,
      });
      hands.onResults(drawLiveHands);
      handsRef.current = hands;
      handCameraRef.current = new cameraUtils.Camera(videoRef.current, {
        onFrame: async () => {
          await hands.send({ image: videoRef.current });
        },
        width: 640,
        height: 480,
      });
      handCameraRef.current.start();
      framesRef.current = [];
      setPrediction(null);
      setIsCameraOn(true);
      setIsCapturing(true);
      setMessage(`Perform the sign for "${targetWord}" and click Detect.`);
      captureTimerRef.current = setInterval(captureFrame, 120);
    } catch (error) {
      setMessage(`Camera unavailable: ${error.message}`);
    }
  };

  const advanceQuestion = () => {
    stopCamera();
    setAttempts(0);
    setCurrentQuestion((question) => question + 1);
    if (currentQuestion + 1 >= targetWords.length) {
      setMessage("All words attempted. Submit your test to see the result.");
    } else {
      setMessage("Start the camera for the next word.");
    }
  };

  const detectWord = async () => {
    if (!isCapturing || testFinished) return;
    clearInterval(captureTimerRef.current);
    captureTimerRef.current = null;
    setIsCapturing(false);
    if (framesRef.current.length < MIN_CAPTURE_FRAMES) {
      setMessage("Capture a slightly longer gesture before detecting.");
      setIsCapturing(true);
      captureTimerRef.current = setInterval(captureFrame, 120);
      return;
    }

    const formData = new FormData();
    framesRef.current.forEach((frame, index) => formData.append("frames", frame, `frame-${index}.jpg`));
    setMessage("Detecting word...");
    try {
      const response = await fetch(`${BASE_URL}/predict/word`, { method: "POST", body: formData });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || "Prediction failed.");
      setPrediction(data);
      if (data.label === targetWord) {
        if (questionResults[currentQuestion] !== true) {
          setQuestionResults((results) => {
            const nextResults = [...results];
            nextResults[currentQuestion] = true;
            return nextResults;
          });
          setCorrect((value) => value + 1);
        }
        setMessage("Correct");
        advanceQuestion();
      } else {
        const nextAttempts = attempts + 1;
        setAttempts(nextAttempts);
        stopCamera();
        setMessage(nextAttempts >= 5 ? "Maximum attempts reached." : "Wrong prediction. Try Again or Next / Skip.");
      }
    } catch (error) {
      setMessage(error.message);
      stopCamera();
    }
  };

  const tryAgain = () => {
    setPrediction(null);
    startCamera();
  };

  const skipQuestion = () => {
    if (attempts === 0 || testFinished) return;
    setQuestionResults((results) => {
      const nextResults = [...results];
      nextResults[currentQuestion] = false;
      return nextResults;
    });
    advanceQuestion();
  };

  const previousQuestion = () => {
    if (currentQuestion === 0 || isCapturing) return;
    stopCamera();
    setCurrentQuestion((question) => question - 1);
    setAttempts(0);
    setPrediction(null);
    setMessage("Start the camera to retry this word.");
  };

  const complete = async () => {
    stopCamera();
    try {
      const userId = localStorage.getItem("userId");
      const user = localStorage.getItem("userName");
      const category = "Word";
      const response = await fetch(SCORE_API_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          userId,
          user,
          category,
          correct_signs: correct,
          total_signs: TEST_LENGTH,
        }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || "Failed to submit test result");
      navigate("/word-result");
    } catch (error) {
      setMessage(error.message === "Failed to fetch"
        ? "Unable to reach the test server. Please start the backend and try again."
        : error.message);
    }
  };

  return (
    <div className="flex min-h-screen flex-col items-center bg-emerald-50">
      <div className="mb-3 w-full bg-emerald-600 p-1 text-center font-sans text-4xl font-bold text-stone-100">
        Word Test
      </div>

      <div className="flex w-full flex-col rounded-2xl text-center font-sans text-2xl font-bold text-red-500">
        <h2>Make Sign of: <span className="text-3xl text-gray-500">&quot;{targetWord || "Loading..."}&quot;</span></h2>
        <h2>Detected Word: <span className="text-3xl font-bold text-green-600">{prediction?.label || "----"} ({prediction ? (prediction.confidence * 100).toFixed(1) : "0"}%)</span></h2>
        <p className="text-lg text-emerald-800">Question {Math.min(currentQuestion + 1, TEST_LENGTH)} / {TEST_LENGTH} | Attempts: {attempts} / 5</p>
      </div>

      <div className="relative h-[480px] w-[640px] max-w-full">
        <video ref={videoRef} autoPlay playsInline className={`absolute left-0 top-0 h-full w-full rounded-lg border-2 border-black object-cover shadow-lg ${isCameraOn ? "block" : "hidden"}`} />
        <canvas ref={overlayCanvasRef} width="640" height="480" className={`absolute left-0 top-0 h-full w-full border-2 border-black ${isCameraOn ? "block" : "hidden"}`} />
        <canvas ref={canvasRef} className="hidden" />
      </div>

      <div className="mt-5 flex w-full justify-between gap-5 px-10 lg:px-35">
        <button onClick={previousQuestion} disabled={currentQuestion === 0 || isCapturing} className="rounded-lg bg-violet-500 px-4 py-2 text-white shadow-lg hover:bg-violet-600 disabled:opacity-50">Prev</button>
        <div className="flex gap-3">
          <button onClick={startCamera} disabled={isCameraOn || testFinished} className="rounded-lg bg-green-500 px-4 py-2 text-white shadow-lg hover:bg-green-600 disabled:opacity-50">Start</button>
          <button onClick={detectWord} disabled={!isCapturing} className="rounded-lg bg-orange-500 px-4 py-2 text-white shadow-lg hover:bg-orange-600 disabled:opacity-50">Detect</button>
        </div>
        <button onClick={skipQuestion} disabled={attempts === 0 || testFinished} className="rounded-lg bg-violet-500 px-4 py-2 text-white shadow-lg hover:bg-violet-600 disabled:opacity-50">Next / Skip</button>
      </div>

      <p className="mt-4 text-lg font-semibold text-slate-700">{message}</p>

      {prediction && prediction.label !== targetWord && !testFinished && (
        <div className="mt-3 flex gap-3">
          <button onClick={tryAgain} className="rounded-lg bg-orange-500 px-5 py-2 font-bold text-white hover:bg-orange-600">Try Again</button>
          <button onClick={skipQuestion} disabled={attempts === 0} className="rounded-lg bg-violet-500 px-5 py-2 font-bold text-white hover:bg-violet-600 disabled:opacity-50">Next / Skip</button>
        </div>
      )}

      <div className="mb-8 mt-5 flex gap-4">
        <button onClick={complete} className="rounded-lg bg-green-500 px-4 py-2 font-bold text-white shadow-lg hover:bg-green-600">Complete Test</button>
        <button onClick={complete} className="rounded-lg bg-red-500 px-4 py-2 font-bold text-white shadow-lg hover:bg-red-600">Quit Test</button>
      </div>
    </div>
  );
}

export default WordTest;
