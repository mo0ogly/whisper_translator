import React, { useState } from 'react';
import './BenchmarkModal.css';

export default function BenchmarkModal({ onClose }) {
    const [loading, setLoading] = useState(true);
    const [data, setData] = useState(null);
    const [error, setError] = useState(null);

    React.useEffect(() => {
        fetch('/api/benchmark')
            .then(res => {
                if (!res.ok) throw new Error("Failed to fetch benchmark");
                return res.json();
            })
            .then(json => {
                setData(json);
                setLoading(false);
            })
            .catch(err => {
                setError(err.message);
                setLoading(false);
            });
    }, []);

    const getStatusClass = (status) => {
        if (status === "Good") return "text-green";
        if (status.includes("Slow")) return "text-orange";
        return "text-red";
    };

    return (
        <div className="modal-overlay">
            <div className="modal-content">
                <h2>Hardware Benchmark</h2>
                {loading ? (
                    <p>Analyzing system...</p>
                ) : error ? (
                    <p className="text-red">Error: {error}</p>
                ) : (
                    <>
                        <div className="benchmark-section">
                            <h3>System Specs</h3>
                            <ul>
                                <li><strong>Processor Cores:</strong> {data.hardware.cpu_cores}</li>
                                <li><strong>System RAM:</strong> {data.hardware.ram_gb} GB</li>
                                <li><strong>GPU:</strong> {data.hardware.gpu}</li>
                                {data.hardware.gpu !== "None" && data.hardware.gpu !== "Unknown CUDA Device" && (
                                    <li><strong>GPU VRAM:</strong> {data.hardware.gpu_vram_gb} GB</li>
                                )}
                                <li><strong>Inference Type:</strong> {data.hardware.compute_type}</li>
                            </ul>
                        </div>

                        <div className="benchmark-section">
                            <h3>Recommendations</h3>
                            <ul className="recommendations-list">
                                <li>
                                    <strong>Whisper (Base/Tiny):</strong> <span className={getStatusClass(data.recommendations.whisper_base)}>{data.recommendations.whisper_base}</span>
                                </li>
                                <li>
                                    <strong>Whisper (Large):</strong> <span className={getStatusClass(data.recommendations.whisper_large)}>{data.recommendations.whisper_large}</span>
                                </li>
                                <li>
                                    <strong>Diarization (Pyannote):</strong> <span className={getStatusClass(data.recommendations.diarization)}>{data.recommendations.diarization}</span>
                                </li>
                            </ul>
                        </div>
                    </>
                )}
                <button className="confirm-btn" onClick={onClose}>Close</button>
            </div>
        </div>
    );
}
