import { useState } from 'react'
import './App.css'

interface HeaderLabelInfo {
  label: string
  reason: string
  header_text: string
  filename: string | null
  header_index: number
}

interface CSVData {
  header: string
  page: number
  page_size: number
  total_records: number
  total_pages: number
  rows: Record<string, string | number>[]
  label_info: HeaderLabelInfo
}

interface FileStatus {
  has_file: boolean
  filename: string | null
  headers: string[]
  row_count: number
}

function App() {
  const [fileStatus, setFileStatus] = useState<FileStatus>({
    has_file: false,
    filename: null,
    headers: [],
    row_count: 0
  })
  const [selectedHeader, setSelectedHeader] = useState('')
  const [currentPage, setCurrentPage] = useState(1)
  const [data, setData] = useState<CSVData | null>(null)
  const rowsPerPage = 10
  
  // Upload states
  const [uploadFile, setUploadFile] = useState<File | null>(null)
  const [uploading, setUploading] = useState(false)
  const [uploadError, setUploadError] = useState<string | null>(null)
  
  // Export states
  const [exporting, setExporting] = useState(false)
  const [exportSuccess, setExportSuccess] = useState<string | null>(null)
  const [exportError, setExportError] = useState<string | null>(null)

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) {
      const validTypes = ['text/csv', 'application/vnd.ms-excel', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet']
      const fileExtension = file.name.toLowerCase().split('.').pop()
      
      if (!validTypes.includes(file.type) && !['csv', 'xlsx', 'xls'].includes(fileExtension || '')) {
        setUploadError('Please select a valid CSV or Excel file')
        setUploadFile(null)
        return
      }
      
      setUploadFile(file)
      setUploadError(null)
    }
  }

  const handleUpload = async () => {
    if (!uploadFile) {
      setUploadError('Please select a file first')
      return
    }

    const formData = new FormData()
    formData.append('file', uploadFile)

    try {
      setUploading(true)
      setUploadError(null)

      const response = await fetch('http://localhost:8000/api/upload', {
        method: 'POST',
        body: formData,
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Upload failed')
      }

      const result = await response.json()
      
      // Update file status
      setFileStatus({
        has_file: true,
        filename: result.filename,
        headers: result.headers,
        row_count: result.row_count
      })
      
      setSelectedHeader('')
      setCurrentPage(1)
      setData(null)
      setUploadFile(null)
      
      // Clear the file input
      const fileInput = document.getElementById('file-input') as HTMLInputElement
      if (fileInput) fileInput.value = ''
    } catch (err) {
      setUploadError(err instanceof Error ? err.message : 'An error occurred during upload')
    } finally {
      setUploading(false)
    }
  }

  const fetchData = async (header: string, page: number) => {
    try {
      const response = await fetch(
        `http://localhost:8000/api/data?header=${encodeURIComponent(header)}&page=${page}&page_size=${rowsPerPage}`
      )
      if (response.ok) {
        const dataResult = await response.json()
        setData(dataResult)
      } else {
        const error = await response.json()
        throw new Error(error.detail || 'Failed to fetch data')
      }
    } catch (err) {
      console.error('Failed to fetch data:', err)
      setData(null)
    }
  }

  const handleExportHeaders = async (format: 'csv' | 'excel') => {
    if (!fileStatus.has_file) {
      setExportError('No file uploaded')
      return
    }

    try {
      setExporting(true)
      setExportError(null)
      setExportSuccess(null)

      const response = await fetch(`http://localhost:8000/api/export-headers?output_format=${format}`, {
        method: 'POST'
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Export failed')
      }

      const result = await response.json()
      setExportSuccess(`Headers exported successfully to ${result.output_file}`)
    } catch (err) {
      setExportError(err instanceof Error ? err.message : 'An error occurred during export')
    } finally {
      setExporting(false)
    }
  }

  return (
    <div style={{ maxWidth: 1000, margin: '2rem auto', fontFamily: 'Arial, sans-serif', padding: '1rem' }}>
      <h1>CSV/Excel Data Manager</h1>

      {/* File Upload Section */}
      <div style={{ 
        backgroundColor: '#f9f9f9', 
        padding: '1.5rem', 
        borderRadius: '8px', 
        marginBottom: '2rem',
        border: '1px solid #e0e0e0'
      }}>
        <h2 style={{ marginTop: 0, fontSize: '1.3rem' }}>Upload File</h2>
        <p style={{ color: '#666', marginBottom: '1rem' }}>Upload a CSV or Excel file to manage its headers</p>
        
        <div style={{ marginBottom: '1rem' }}>
          <label htmlFor="file-input" style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 'bold' }}>
            Select File:
          </label>
          <input
            id="file-input"
            type="file"
            accept=".csv,.xlsx,.xls"
            onChange={handleFileSelect}
            disabled={fileStatus.has_file}
            style={{ 
              padding: '0.5rem',
              border: '1px solid #ccc',
              borderRadius: '4px',
              width: '100%',
              opacity: fileStatus.has_file ? 0.6 : 1
            }}
          />
          {uploadFile && <p style={{ color: '#4CAF50', margin: '0.5rem 0' }}>Selected: {uploadFile.name}</p>}
        </div>

        <button
          onClick={handleUpload}
          disabled={!uploadFile || uploading || fileStatus.has_file}
          style={{
            padding: '0.75rem 1.5rem',
            backgroundColor: uploadFile && !uploading && !fileStatus.has_file ? '#4CAF50' : '#cccccc',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            cursor: uploadFile && !uploading && !fileStatus.has_file ? 'pointer' : 'not-allowed',
            fontSize: '1rem',
            fontWeight: 'bold',
            marginRight: '0.5rem'
          }}
        >
          {uploading ? 'Uploading...' : 'Upload File'}
        </button>

        {fileStatus.has_file && (
          <button
            onClick={() => {
              setFileStatus({ has_file: false, filename: null, headers: [], row_count: 0 })
              setSelectedHeader('')
              setData(null)
              setUploadFile(null)
              setExportSuccess(null)
              setExportError(null)
            }}
            style={{
              padding: '0.75rem 1.5rem',
              backgroundColor: '#2196F3',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: 'pointer',
              fontSize: '1rem',
              fontWeight: 'bold'
            }}
          >
            Upload Different File
          </button>
        )}

        {uploadError && (
          <div style={{ 
            marginTop: '1rem', 
            padding: '1rem', 
            backgroundColor: '#ffebee', 
            color: '#c62828',
            borderRadius: '4px',
            border: '1px solid #ef5350'
          }}>
            <strong>Error:</strong> {uploadError}
          </div>
        )}

        {fileStatus.has_file && (
          <div style={{ 
            marginTop: '1rem', 
            padding: '1rem', 
            backgroundColor: '#e8f5e9', 
            color: '#2e7d32',
            borderRadius: '4px',
            border: '1px solid #4caf50'
          }}>
            <strong>✓ File Uploaded</strong>
            <p style={{ margin: '0.5rem 0' }}>
              <strong>Name:</strong> {fileStatus.filename}
            </p>
            <p style={{ margin: '0.5rem 0' }}>
              <strong>Headers:</strong> {fileStatus.headers.length}
            </p>
            <p style={{ margin: '0.5rem 0' }}>
              <strong>Rows:</strong> {fileStatus.row_count}
            </p>
          </div>
        )}
      </div>

      {/* Data Viewer Section - Only show if file is uploaded */}
      {fileStatus.has_file && (
        <div style={{ 
          backgroundColor: '#f0f5ff', 
          padding: '1.5rem', 
          borderRadius: '8px',
          border: '1px solid #b3d9ff'
        }}>
          <h2 style={{ marginTop: 0 }}>Data Viewer</h2>
          
          <div style={{ marginBottom: '1.5rem' }}>
            <label htmlFor="header-select" style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 'bold' }}>
              Select a column header:
            </label>
            <select
              id="header-select"
              value={selectedHeader}
              onChange={(e) => {
                const newHeader = e.target.value
                setSelectedHeader(newHeader)
                setCurrentPage(1)
                if (newHeader) {
                  fetchData(newHeader, 1)
                } else {
                  setData(null)
                }
              }}
              style={{ width: '100%', padding: '0.75rem', fontSize: '1rem', borderRadius: '4px', border: '1px solid #ccc' }}
            >
              <option value="" disabled>
                -- Select a header --
              </option>
              {fileStatus.headers.map((header) => (
                <option key={header} value={header}>
                  {header}
                </option>
              ))}
            </select>
          </div>

          {/* Export Buttons */}
          <div style={{ marginBottom: '1.5rem' }}>
            <h3 style={{ fontSize: '1.1rem', marginBottom: '0.5rem' }}>Export Headers</h3>
            <button
              onClick={() => handleExportHeaders('csv')}
              disabled={exporting}
              style={{
                padding: '0.75rem 1.5rem',
                backgroundColor: exporting ? '#cccccc' : '#FF9800',
                color: 'white',
                border: 'none',
                borderRadius: '4px',
                cursor: exporting ? 'not-allowed' : 'pointer',
                fontSize: '1rem',
                fontWeight: 'bold',
                marginRight: '0.5rem'
              }}
            >
              {exporting ? 'Exporting...' : 'Export as CSV'}
            </button>
            <button
              onClick={() => handleExportHeaders('excel')}
              disabled={exporting}
              style={{
                padding: '0.75rem 1.5rem',
                backgroundColor: exporting ? '#cccccc' : '#27AE60',
                color: 'white',
                border: 'none',
                borderRadius: '4px',
                cursor: exporting ? 'not-allowed' : 'pointer',
                fontSize: '1rem',
                fontWeight: 'bold'
              }}
            >
              {exporting ? 'Exporting...' : 'Export as Excel'}
            </button>
          </div>

          {exportSuccess && (
            <div style={{ 
              padding: '1rem', 
              backgroundColor: '#e8f5e9', 
              color: '#2e7d32',
              borderRadius: '4px',
              border: '1px solid #4caf50',
              marginBottom: '1.5rem'
            }}>
              <strong>✓ {exportSuccess}</strong>
            </div>
          )}

          {exportError && (
            <div style={{ 
              padding: '1rem', 
              backgroundColor: '#ffebee', 
              color: '#c62828',
              borderRadius: '4px',
              border: '1px solid #ef5350',
              marginBottom: '1.5rem'
            }}>
              <strong>Error:</strong> {exportError}
            </div>
          )}

          <div style={{ marginTop: '1.5rem' }}>
            <h3 style={{ marginBottom: '0.5rem' }}>Column Data: {selectedHeader || 'None selected'}</h3>
            {selectedHeader && data ? (
              <div>
                <div style={{ marginBottom: '1rem', padding: '1rem', backgroundColor: '#ffffff', borderRadius: '8px', border: '1px solid #dcdcdc' }}>
                  <p style={{ margin: '0.25rem 0', fontSize: '0.95rem' }}><strong>Label:</strong> {data.label_info.label}</p>
                  <p style={{ margin: '0.25rem 0', fontSize: '0.95rem' }}><strong>Reason:</strong> {data.label_info.reason}</p>
                  <p style={{ margin: '0.25rem 0', fontSize: '0.95rem' }}><strong>Header Text:</strong> {data.label_info.header_text}</p>
                  <p style={{ margin: '0.25rem 0', fontSize: '0.95rem' }}><strong>File Name:</strong> {data.label_info.filename || 'Unknown'}</p>
                  <p style={{ margin: '0.25rem 0', fontSize: '0.95rem' }}><strong>Header Index:</strong> {data.label_info.header_index}</p>
                </div>
                {data.rows.length > 0 ? (
                  <>
                    <p style={{ fontSize: '0.9rem', color: '#666', marginBottom: '0.75rem' }}>
                      Showing records {(currentPage - 1) * rowsPerPage + 1} - {Math.min(currentPage * rowsPerPage, data.total_records)} of {data.total_records} for <strong>{selectedHeader}</strong>
                    </p>
                    <table style={{ width: '100%', borderCollapse: 'collapse', marginTop: '1rem' }}>
                      <thead>
                        <tr style={{ backgroundColor: '#f0f0f0' }}>
                          <th style={{ padding: '0.75rem', textAlign: 'left', borderBottom: '2px solid #ddd' }}>#</th>
                          <th style={{ padding: '0.75rem', textAlign: 'left', borderBottom: '2px solid #ddd' }}>
                            {selectedHeader}
                          </th>
                        </tr>
                      </thead>
                      <tbody>
                        {data.rows.map((row, idx) => (
                          <tr key={idx} style={{ backgroundColor: idx % 2 === 0 ? '#fafafa' : 'white' }}>
                            <td style={{ padding: '0.75rem', borderBottom: '1px solid #eee' }}>{(currentPage - 1) * rowsPerPage + idx + 1}</td>
                            <td style={{ padding: '0.75rem', borderBottom: '1px solid #eee' }}>
                              {row[selectedHeader as string] ?? ''}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                    {data.total_pages > 1 && (
                      <div style={{ marginTop: '1rem', display: 'flex', flexWrap: 'wrap', gap: '0.5rem', alignItems: 'center' }}>
                        <button
                          onClick={() => {
                            const prevPage = Math.max(1, currentPage - 1)
                            if (prevPage !== currentPage && selectedHeader) {
                              setCurrentPage(prevPage)
                              fetchData(selectedHeader, prevPage)
                            }
                          }}
                          disabled={currentPage === 1}
                          style={{
                            padding: '0.5rem 0.8rem',
                            borderRadius: '4px',
                            border: '1px solid #ccc',
                            backgroundColor: currentPage === 1 ? '#f0f0f0' : 'white',
                            color: currentPage === 1 ? '#999' : '#333',
                            cursor: currentPage === 1 ? 'not-allowed' : 'pointer'
                          }}
                        >
                          Previous
                        </button>
                        <span style={{ color: '#333', fontSize: '0.9rem' }}>
                          Page {currentPage} of {data.total_pages}
                        </span>
                        <button
                          onClick={() => {
                            const nextPage = Math.min(data.total_pages, currentPage + 1)
                            if (nextPage !== currentPage && selectedHeader) {
                              setCurrentPage(nextPage)
                              fetchData(selectedHeader, nextPage)
                            }
                          }}
                          disabled={currentPage === data.total_pages}
                          style={{
                            padding: '0.5rem 0.8rem',
                            borderRadius: '4px',
                            border: '1px solid #ccc',
                            backgroundColor: currentPage === data.total_pages ? '#f0f0f0' : 'white',
                            color: currentPage === data.total_pages ? '#999' : '#333',
                            cursor: currentPage === data.total_pages ? 'not-allowed' : 'pointer'
                          }}
                        >
                          Next
                        </button>
                      </div>
                    )}
                  </>
                ) : (
                  <p style={{ color: '#666' }}>No data available for the selected header.</p>
                )}
              </div>
            ) : selectedHeader && !data ? (
              <p style={{ color: '#666' }}>Loading data...</p>
            ) : (
              <p style={{ color: '#666' }}>Select a header to view the data grid.</p>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

export default App
