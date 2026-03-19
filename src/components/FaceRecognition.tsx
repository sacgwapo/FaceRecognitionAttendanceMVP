import { useRef, useState, useCallback, useEffect } from 'react';
import { Camera, Loader } from 'lucide-react';
import { supabase } from '../lib/supabaseClient';

interface Capture {
  id: string;
  timestamp: string;
  image_url: string;
}

export function FaceRecognition() {
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [isStreaming, setIsStreaming] = useState(false);
  const [isCaptureLoading, setIsCaptureLoading] = useState(false);
  const [lastCapture, setLastCapture] = useState<Capture | null>(null);

  useEffect(() => {
    const startCamera = async () => {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          video: { facingMode: 'user' },
        });
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
          setIsStreaming(true);
        }
      } catch (error) {
        console.error('Error accessing camera:', error);
      }
    };

    startCamera();

    return () => {
      if (videoRef.current?.srcObject) {
        const tracks = (videoRef.current.srcObject as MediaStream).getTracks();
        tracks.forEach((track) => track.stop());
      }
    };
  }, []);

  const handleCapture = useCallback(async () => {
    if (!videoRef.current || !canvasRef.current) return;

    setIsCaptureLoading(true);
    try {
      const context = canvasRef.current.getContext('2d');
      if (!context) return;

      canvasRef.current.width = videoRef.current.videoWidth;
      canvasRef.current.height = videoRef.current.videoHeight;
      context.drawImage(videoRef.current, 0, 0);

      const blob = await new Promise<Blob>((resolve) => {
        canvasRef.current!.toBlob((b) => {
          if (b) resolve(b);
        }, 'image/jpeg', 0.9);
      });

      const timestamp = new Date().toISOString();
      const fileName = `capture_${timestamp.replace(/[:.]/g, '-')}.jpg`;

      const { data: uploadData, error: uploadError } = await supabase.storage
        .from('captures')
        .upload(`public/${fileName}`, blob);

      if (uploadError) throw uploadError;

      const { data: urlData } = supabase.storage
        .from('captures')
        .getPublicUrl(`public/${fileName}`);

      const { data: insertData, error: insertError } = await supabase
        .from('captures')
        .insert([
          {
            image_url: urlData.publicUrl,
            timestamp: timestamp,
          },
        ])
        .select()
        .single();

      if (insertError) throw insertError;

      setLastCapture({
        id: insertData.id,
        image_url: insertData.image_url,
        timestamp: insertData.timestamp,
      });
    } catch (error) {
      console.error('Capture error:', error);
    } finally {
      setIsCaptureLoading(false);
    }
  }, []);

  return (
    <div className="w-full h-screen flex items-center justify-center bg-gray-900">
      <div className="w-full max-w-2xl">
        <div className="relative w-full aspect-video bg-black rounded-lg overflow-hidden shadow-2xl">
          {isStreaming ? (
            <>
              <video
                ref={videoRef}
                autoPlay
                playsInline
                className="w-full h-full object-cover"
              />
              <button
                onClick={handleCapture}
                disabled={isCaptureLoading}
                className="absolute bottom-4 left-1/2 -translate-x-1/2 bg-red-500 hover:bg-red-600 disabled:bg-red-700 disabled:opacity-70 text-white rounded-full p-4 transition-colors shadow-lg"
              >
                {isCaptureLoading ? (
                  <Loader className="w-6 h-6 animate-spin" />
                ) : (
                  <Camera className="w-6 h-6" />
                )}
              </button>
            </>
          ) : (
            <div className="w-full h-full flex items-center justify-center">
              <Loader className="w-12 h-12 animate-spin text-gray-400" />
            </div>
          )}
        </div>

        {lastCapture && (
          <div className="mt-6 p-4 bg-gray-800 rounded-lg">
            <p className="text-gray-300 text-sm mb-3">
              Last capture: {new Date(lastCapture.timestamp).toLocaleString()}
            </p>
            <img
              src={lastCapture.image_url}
              alt="Last capture"
              className="w-full h-auto rounded-lg"
            />
          </div>
        )}
      </div>

      <canvas ref={canvasRef} className="hidden" />
    </div>
  );
}
