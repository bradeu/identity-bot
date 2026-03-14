'use client';

import { useState, useCallback } from 'react';

interface CsvFile {
  id: string;
  name: string;
  size: number;
  file: File;
  status: 'pending' | 'processing' | 'completed' | 'error';
  result?: string;
}

export default function Home() {
  const [files, setFiles] = useState<CsvFile[]>([]);
  const [dragActive, setDragActive] = useState(false);
  const [processing, setProcessing] = useState(false);

  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  }, []);

  const addCsvFiles = (rawFiles: File[]) => {
    const csvFiles = rawFiles.filter(f => f.name.endsWith('.csv') || f.type === 'text/csv');
    const newFiles: CsvFile[] = csvFiles.map(file => ({
      id: Math.random().toString(36).substr(2, 9),
      name: file.name,
      size: file.size,
      file,
      status: 'pending',
    }));
    setFiles(prev => [...prev, ...newFiles]);
  };

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    addCsvFiles(Array.from(e.dataTransfer.files));
  }, []);

  const handleFileInput = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    addCsvFiles(Array.from(e.target.files || []));
  }, []);

  const removeFile = useCallback((id: string) => {
    setFiles(prev => prev.filter(file => file.id !== id));
  }, []);

  const processFiles = async () => {
    if (files.length === 0) return;

    setProcessing(true);

    for (const file of files) {
      if (file.status !== 'pending') continue;

      setFiles(prev => prev.map(f =>
        f.id === file.id ? { ...f, status: 'processing' as const } : f
      ));

      try {
        const formData = new FormData();
        formData.append('file', file.file);

        const response = await fetch(
          `${process.env.NEXT_PUBLIC_API_BASE_URL}/api/v1/processor/csv/dashboard/`,
          { method: 'POST', body: formData }
        );

        if (response.ok) {
          const result = await response.json();
          setFiles(prev => prev.map(f =>
            f.id === file.id ? {
              ...f,
              status: 'completed' as const,
              result: `Task queued (${result.task_id})`,
            } : f
          ));
        } else {
          const err = await response.json().catch(() => ({}));
          setFiles(prev => prev.map(f =>
            f.id === file.id ? {
              ...f,
              status: 'error' as const,
              result: err.detail || 'Error processing file',
            } : f
          ));
        }
      } catch {
        setFiles(prev => prev.map(f =>
          f.id === file.id ? { ...f, status: 'error' as const, result: 'Network error' } : f
        ));
      }
    }

    setProcessing(false);
  };

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const getStatusColor = (status: CsvFile['status']) => {
    switch (status) {
      case 'pending': return 'text-gray-500 bg-gray-100';
      case 'processing': return 'text-blue-600 bg-blue-100';
      case 'completed': return 'text-green-600 bg-green-100';
      case 'error': return 'text-red-600 bg-red-100';
    }
  };

  const getStatusIcon = (status: CsvFile['status']) => {
    switch (status) {
      case 'pending':
        return <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>;
      case 'processing':
        return <div className="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin" />;
      case 'completed':
        return <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
        </svg>;
      case 'error':
        return <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
        </svg>;
    }
  };

  const pendingCount = files.filter(f => f.status === 'pending').length;

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-purple-50">
      {/* Navbar */}
      <nav className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <h1 className="text-xl font-bold text-gray-900">CSV Dashboard</h1>
            <div className="w-8 h-8 bg-blue-600 rounded-full flex items-center justify-center">
              <span className="text-white text-sm font-medium">U</span>
            </div>
          </div>
        </div>
      </nav>

      <div className="container mx-auto px-4 py-6 max-w-5xl">
        {/* Header */}
        <div className="mb-6 flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Upload Survey Data</h1>
            <p className="text-gray-600 mt-1">Upload CSV files to ingest party-support data into the database</p>
          </div>
          {files.length > 0 && (
            <button
              onClick={() => setFiles([])}
              className="px-4 py-2 text-gray-600 hover:text-gray-800 hover:bg-gray-100 rounded-lg transition-colors duration-200"
            >
              Clear Files
            </button>
          )}
        </div>

        {/* Upload container */}
        <div
          className={`bg-white rounded-xl shadow-sm border border-gray-200 h-[calc(100vh-220px)] flex flex-col ${
            dragActive && files.length > 0 ? 'ring-2 ring-blue-400 ring-offset-2' : ''
          }`}
          onDragEnter={handleDrag}
          onDragLeave={handleDrag}
          onDragOver={handleDrag}
          onDrop={handleDrop}
        >
          <div className="flex-1 p-6">
            {files.length === 0 ? (
              <div
                className={`h-full border-2 border-dashed rounded-xl flex items-center justify-center transition-colors duration-200 ${
                  dragActive ? 'border-blue-400 bg-blue-50' : 'border-gray-300 hover:border-gray-400'
                }`}
              >
                <div className="text-center space-y-4">
                  <div className="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center mx-auto">
                    <svg className="w-8 h-8 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                    </svg>
                  </div>
                  <div>
                    <h3 className="text-lg font-medium text-gray-900 mb-2">Upload your CSV files</h3>
                    <p className="text-gray-500 mb-4">Drag and drop CSV files here to get started</p>
                  </div>
                  <input
                    type="file"
                    multiple
                    accept=".csv,text/csv"
                    onChange={handleFileInput}
                    className="hidden"
                    id="file-upload"
                  />
                  <label
                    htmlFor="file-upload"
                    className="bg-blue-500 text-white rounded-2xl hover:bg-blue-600 transition-colors duration-200 px-6 py-3 font-medium cursor-pointer inline-flex items-center space-x-2"
                  >
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
                    </svg>
                    <span>Choose Files</span>
                  </label>
                </div>
              </div>
            ) : (
              <div className="h-full flex flex-col relative">
                {dragActive && (
                  <div className="absolute inset-0 bg-blue-50/80 border-2 border-dashed border-blue-400 rounded-xl flex items-center justify-center z-10">
                    <div className="text-center">
                      <div className="w-12 h-12 bg-blue-500 rounded-full flex items-center justify-center mx-auto mb-3">
                        <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
                        </svg>
                      </div>
                      <p className="text-blue-700 font-medium">Drop files to add more CSVs</p>
                    </div>
                  </div>
                )}

                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-lg font-medium text-gray-900">Uploaded Files</h3>
                  <div className="flex items-center space-x-3">
                    <span className="text-sm text-gray-600">{files.length} files</span>
                    <input
                      type="file"
                      multiple
                      accept=".csv,text/csv"
                      onChange={handleFileInput}
                      className="hidden"
                      id="add-files"
                    />
                    <label htmlFor="add-files" className="text-blue-600 hover:text-blue-700 text-sm font-medium cursor-pointer">
                      Add More
                    </label>
                  </div>
                </div>

                <div className="flex-1 overflow-y-auto scrollbar-thin space-y-3">
                  {files.map((file) => (
                    <div key={file.id} className="border border-gray-200 rounded-xl p-4 hover:shadow-md transition-shadow duration-200">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center space-x-3 flex-1 min-w-0">
                          <div className="w-10 h-10 bg-green-50 rounded-lg flex items-center justify-center flex-shrink-0">
                            <svg className="w-5 h-5 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                            </svg>
                          </div>
                          <div className="flex-1 min-w-0">
                            <p className="font-medium text-gray-900 truncate">{file.name}</p>
                            <p className="text-sm text-gray-600">{formatFileSize(file.size)}</p>
                            {file.result && (
                              <p className="text-sm text-gray-500 mt-1">{file.result}</p>
                            )}
                          </div>
                        </div>
                        <div className="flex items-center space-x-3">
                          <div className={`flex items-center space-x-1 px-2 py-1 rounded-full text-xs font-medium ${getStatusColor(file.status)}`}>
                            {getStatusIcon(file.status)}
                            <span className="capitalize">{file.status}</span>
                          </div>
                          {file.status === 'pending' && (
                            <button
                              onClick={() => removeFile(file.id)}
                              className="text-gray-400 hover:text-gray-600 p-1 rounded transition-colors duration-200"
                            >
                              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                              </svg>
                            </button>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {files.length > 0 && (
            <div className="border-t border-gray-200 p-4">
              <button
                onClick={processFiles}
                disabled={processing || pendingCount === 0}
                className="w-full bg-blue-500 text-white rounded-2xl hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors duration-200 px-6 py-3 font-medium flex items-center justify-center space-x-2"
              >
                {processing ? (
                  <>
                    <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                    <span>Uploading...</span>
                  </>
                ) : (
                  <>
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                    </svg>
                    <span>Ingest {pendingCount} CSV{pendingCount !== 1 ? 's' : ''}</span>
                  </>
                )}
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
