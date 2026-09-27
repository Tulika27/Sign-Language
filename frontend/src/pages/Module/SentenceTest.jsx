import { useEffect, useRef, useState, useContext } from "react";
import { useNavigate } from "react-router-dom";
import { Hands } from "@mediapipe/hands";
import * as cameraUtils from "@mediapipe/camera_utils";
import UserContext from "../../Context/UserContext";

const SENTENCE_API_URL = "http://localhost:5002/predict/sentence";
const SCORE_API_URL = "http://localhost:5001/api/create";
const TEST_LENGTH = 5;
const MAX_RECORD_MS = 6000;
const MIN_RECORD_MS = 800;

// These 5 sentences are the ones the trained sentence model reliably
// recognizes (see Step 8B). Order is fixed for consistent demo behavior.
const DEMO_SENTENCES = [
  { english: "thank you so much", gloss: "THANK YOU SO MUCH" },
  { english: "how old are you", gloss: "HOW OLD YOU" },
  { english: "can i help you", gloss: "I HELP YOU" },
  { english: "do not worry", gloss: "DO NOT WORRY" },
  { english: "you are welcome", gloss: "YOU WELCOME" },
];

const normalize = (text) => (text || "").trim().toLowerCase().replace(/\s+/g, " ");

function SentenceTest() {
  const videoRef = useRef(null);
  const overlayCanvasRef = useRef(null);
  const streamRef = useRef(null);
  const handsRef = useRef(null);
  const handCameraRef = useRef(null);
  const mediaRecorderRef = useRef(null);
  const recordedChunksRef = useRef([]);
  const recordTimeoutRef = useRef(null);
  const recordStartRef = useRef(0);
  const fileInputRef = useRef(null);

  const { correct, setCorrect } = useContext(UserContext);
  const navigate = useNavigate();

  const [targetSentences] = useState(DEMO_SENTENCES);
  const [questionResults, setQuestionResults] = useState(new Array(TEST_LENGTH).fill(null));
  const [currentQuestion, setCurrentQuestion] = useState(0);
  const [attempts, setAttempts] = useState(0);
  const [prediction, setPrediction] = useState(null); // { gloss, english }
  const [isCameraOn, setIsCameraOn] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [uploadedFile, setUploadedFile] = useState(null);
  const [message, setMessage] = useState("Start the camera or upload a video to begin.");

  const targetSentence = targetSentences[currentQuestion];
  const testFinished = currentQuestion >= targetSentences.length;
  const autoSubmittedRef = useRef(false);

  useEffect(() => {
    setCorrect(0);
    return () => stopCamera();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (testFinished && !autoSubmittedRef.current) {
      autoSubmittedRef.current = true;
      complete(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [testFinished]);

  function stopCamera() {
    clearTimeout(recordTimeoutRef.current);
    recordTimeoutRef.current = null;
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
      mediaRecorderRef.current.stop();
    }
    mediaRecorderRef.current = null;
    handCameraRef.current?.stop();
    handCameraRef.current = null;
    handsRef.current?.close();
    handsRef.current = null;
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
    if (videoRef.current) videoRef.current.srcObject = null;
    if (overlayCanvasRef.current) {
      overlayCanvasRef.current.getContext("2d")?.clearRect(
        0,
        0,
        overlayCanvasRef.current.width,
        overlayCanvasRef.current.height,
      );
    }
    setIsCameraOn(false);
    setIsRecording(false);
  }

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

  const pickSupportedMimeType = () => {
    const candidates = [
      "video/webm;codecs=vp9",
      "video/webm;codecs=vp8",
      "video/webm",
      "video/mp4",
    ];
    for (const type of candidates) {
      if (window.MediaRecorder && MediaRecorder.isTypeSupported(type)) return type;
    }
    return "";
  };

  const startCamera = async () => {
    if (testFinished || !targetSentence || attempts >= 5) return;
    setUploadedFile(null);
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

      recordedChunksRef.current = [];
      const mimeType = pickSupportedMimeType();
      const recorder = mimeType
        ? new MediaRecorder(stream, { mimeType })
        : new MediaRecorder(stream);
      recorder.ondataavailable = (event) => {
        if (event.data && event.data.size > 0) recordedChunksRef.current.push(event.data);
      };
      mediaRecorderRef.current = recorder;
      recorder.start();
      recordStartRef.current = Date.now();

      setPrediction(null);
      setIsCameraOn(true);
      setIsRecording(true);
      setMessage(`Perform the full sign for "${targetSentence.english}", then click Detect.`);

      recordTimeoutRef.current = setTimeout(() => {
        if (mediaRecorderRef.current && mediaRecorderRef.current.state !== "inactive") {
          setMessage("Max recording length reached. Detecting...");
          detectFromRecording();
        }
      }, MAX_RECORD_MS);
    } catch (error) {
      setMessage(`Camera unavailable: ${error.message}`);
    }
  };

  const advanceQuestion = () => {
    stopCamera();
    setAttempts(0);
    setPrediction(null);
    setUploadedFile(null);
    setCurrentQuestion((question) => question + 1);
    if (currentQuestion + 1 >= targetSentences.length) {
      setMessage("All sentences attempted. Submit your test to see the result.");
    } else {
      setMessage("Start the camera or upload a video for the next sentence.");
    }
  };

  const sendVideoForPrediction = async (blob, extension) => {
    setIsProcessing(true);
    setMessage("Detecting sentence...");

    const formData = new FormData();
    formData.append("video", blob, `capture.${extension}`);

    try {
      const response = await fetch(SENTENCE_API_URL, { method: "POST", body: formData });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || "Prediction failed.");

      setPrediction(data);
      setIsProcessing(false);

      const isMatch = normalize(data.english) === normalize(targetSentence.english);
      if (isMatch) {
        if (questionResults[currentQuestion] !== true) {
          setQuestionResults((results) => {
            const nextResults = [...results];
            nextResults[currentQuestion] = true;
            return nextResults;
          });
          setCorrect((value) => value + 1);
        }
        setMessage(`Correct! "${data.english}"`);
        stopCamera();
        setTimeout(advanceQuestion, 800);
      } else {
        const nextAttempts = attempts + 1;
        setAttempts(nextAttempts);
        stopCamera();
        setMessage(
          nextAttempts >= 5
            ? `Maximum attempts reached. Detected "${data.english}". Use Next / Skip.`
            : `Detected "${data.english}". Try Again`,
        );
      }
    } catch (error) {
      setIsProcessing(false);
      stopCamera();
      setMessage(
        error.message === "Failed to fetch"
          ? "Unable to reach the sentence server. Please start the backend and try again."
          : error.message,
      );
    }
  };

  const detectFromRecording = async () => {
    const recorder = mediaRecorderRef.current;
    if (!recorder || recorder.state === "inactive" || testFinished) return;
    clearTimeout(recordTimeoutRef.current);
    recordTimeoutRef.current = null;

    const elapsed = Date.now() - recordStartRef.current;
    if (elapsed < MIN_RECORD_MS) {
      setMessage("Capture a slightly longer gesture before detecting.");
      return;
    }

    setIsRecording(false);

    const stopped = new Promise((resolve) => {
      recorder.onstop = resolve;
    });
    recorder.stop();
    await stopped;

    const mimeType = recorder.mimeType || "video/webm";
    const extension = mimeType.includes("mp4") ? "mp4" : "webm";
    const videoBlob = new Blob(recordedChunksRef.current, { type: mimeType });
    recordedChunksRef.current = [];

    await sendVideoForPrediction(videoBlob, extension);
  };

  const handleFileChange = (event) => {
    const file = event.target.files?.[0];
    if (!file) return;
    stopCamera();
    setPrediction(null);
    setUploadedFile(file);
    setMessage(`Selected "${file.name}". Click Detect to run prediction.`);
  };

  const detectFromUpload = async () => {
    if (!uploadedFile || testFinished) return;
    const extension = uploadedFile.name.split(".").pop() || "mp4";
    await sendVideoForPrediction(uploadedFile, extension);
  };

  const tryAgain = () => {
    setPrediction(null);
    if (uploadedFile) {
      setMessage(`Selected "${uploadedFile.name}". Click Detect to run prediction again.`);
    } else {
      startCamera();
    }
  };

  const skipQuestion = () => {
    if (attempts < 5 || testFinished) return;
    setQuestionResults((results) => {
      const nextResults = [...results];
      nextResults[currentQuestion] = false;
      return nextResults;
    });
    advanceQuestion();
  };

  const previousQuestion = () => {
    if (currentQuestion === 0 || isRecording) return;
    stopCamera();
    setCurrentQuestion((question) => question - 1);
    setAttempts(0);
    setPrediction(null);
    setUploadedFile(null);
    setMessage("Start the camera or upload a video to retry this sentence.");
  };

  const complete = async (quit = false) => {
    stopCamera();
    try {
      const userId = localStorage.getItem("userId");
      const user = localStorage.getItem("userName");
      const response = await fetch(SCORE_API_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          userId,
          user,
          category: "Sentence",
          correct_signs: correct,
          total_signs: TEST_LENGTH,
        }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || "Failed to submit test result");
      navigate(quit ? "/test" : "/sentence-result");
    } catch (error) {
      setMessage(
        error.message === "Failed to fetch"
          ? "Unable to reach the test server. Please start the backend and try again."
          : error.message,
      );
    }
  };

  return (
    <div className="flex min-h-screen flex-col items-center bg-emerald-50">
      <div className="mb-3 w-full bg-emerald-600 p-1 text-center font-sans text-4xl font-bold text-stone-100">
        Basic Sentence Test
      </div>

      <div className="flex w-full flex-col rounded-2xl text-center font-sans text-2xl font-bold text-red-500">
        <h2>
          Make Signs for: <span className="text-3xl text-gray-500">&quot;{targetSentence?.english || "Loading..."}&quot;</span>
        </h2>
        <h2>
          Predicted Gloss: <span className="text-3xl font-bold text-green-600">{prediction?.gloss || "----"}</span>
        </h2>
        <h2>
          Predicted Sentence: <span className="text-3xl font-bold text-green-600">{prediction?.english || "----"}</span>
        </h2>
        <p className="text-lg text-emerald-800">
          Sentence {Math.min(currentQuestion + 1, TEST_LENGTH)} / {TEST_LENGTH} | Attempts: {attempts} / 5
        </p>
      </div>

      <div className="relative h-[480px] w-[640px] max-w-full">
        <video
          ref={videoRef}
          autoPlay
          playsInline
          muted
          className={`absolute left-0 top-0 h-full w-full rounded-lg border-2 border-black object-cover shadow-lg ${isCameraOn ? "block" : "hidden"}`}
        />
        <canvas
          ref={overlayCanvasRef}
          width="640"
          height="480"
          className={`absolute left-0 top-0 h-full w-full border-2 border-black ${isCameraOn ? "block" : "hidden"}`}
        />
        {!isCameraOn && (
          <div className="flex h-full w-full items-center justify-center rounded-lg border-2 border-dashed border-gray-400 bg-white text-gray-500">
            {uploadedFile ? `Ready: ${uploadedFile.name}` : "Camera preview / uploaded video will appear here"}
          </div>
        )}
      </div>

      <div className="mt-4 flex items-center gap-3">
        <input
          ref={fileInputRef}
          type="file"
          accept="video/*"
          onChange={handleFileChange}
          className="hidden"
        />
        <button
          onClick={() => fileInputRef.current?.click()}
          disabled={testFinished || isRecording}
          className="rounded-lg bg-sky-500 px-4 py-2 text-white shadow-lg hover:bg-sky-600 disabled:opacity-50"
        >
          Upload Video
        </button>
        {uploadedFile && <span className="text-sm text-slate-600">{uploadedFile.name}</span>}
      </div>

      <div className="mt-5 flex w-full justify-between gap-5 px-10 lg:px-35">
        <button
          onClick={previousQuestion}
          disabled={currentQuestion === 0 || isRecording}
          className="rounded-lg bg-violet-500 px-4 py-2 text-white shadow-lg hover:bg-violet-600 disabled:opacity-50"
        >
          Prev
        </button>
        <div className="flex gap-3">
          <button
            onClick={startCamera}
            disabled={isCameraOn || testFinished || attempts >= 5}
            className="rounded-lg bg-green-500 px-4 py-2 text-white shadow-lg hover:bg-green-600 disabled:opacity-50"
          >
            Start
          </button>
          <button
            onClick={isCameraOn ? detectFromRecording : detectFromUpload}
            disabled={(!isRecording && !uploadedFile) || isProcessing}
            className="rounded-lg bg-orange-500 px-4 py-2 text-white shadow-lg hover:bg-orange-600 disabled:opacity-50"
          >
            {isProcessing ? "Detecting..." : "Detect"}
          </button>
        </div>
        <button
          onClick={skipQuestion}
          disabled={attempts < 5 || testFinished}
          className="rounded-lg bg-violet-500 px-4 py-2 text-white shadow-lg hover:bg-violet-600 disabled:opacity-50"
        >
          Next / Skip
        </button>
      </div>

      <p className="mt-4 text-lg font-semibold text-slate-700">{message}</p>

      {prediction && normalize(prediction.english) !== normalize(targetSentence?.english) && attempts < 5 && !testFinished && (
        <button onClick={tryAgain} className="mt-3 rounded-lg bg-orange-500 px-5 py-2 font-bold text-white hover:bg-orange-600">
          Try Again
        </button>
      )}

      <div className="mb-8 mt-5 flex gap-4">
        <button onClick={() => complete(false)} className="rounded-lg bg-green-500 px-4 py-2 font-bold text-white shadow-lg hover:bg-green-600">
          Complete Test
        </button>
        <button onClick={() => complete(true)} className="rounded-lg bg-red-500 px-4 py-2 font-bold text-white shadow-lg hover:bg-red-600">
          Quit Test
        </button>
      </div>
    </div>
  );
}

export default SentenceTest;
