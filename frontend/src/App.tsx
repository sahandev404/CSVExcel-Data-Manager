import { useEffect, useRef, useState } from 'react'
import './App.css'
import { ToastContainer, toast } from 'react-toastify'
import 'react-toastify/dist/ReactToastify.css'

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

interface LabelInfoRow {
  Label: string
  "header text": string
  "file name": string
  "header index": number
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
  const [dropdownOpen, setDropdownOpen] = useState(false)
  const dropdownRef = useRef<HTMLDivElement | null>(null)
  
  // Export states
  const [exporting, setExporting] = useState(false)
  const [exportSuccess, setExportSuccess] = useState<string | null>(null)
  const [exportError, setExportError] = useState<string | null>(null)
  const [manualText, setManualText] = useState('')
  const [manualSaving, setManualSaving] = useState(false)
  const [manualError, setManualError] = useState<string | null>(null)
  const [manualResult, setManualResult] = useState<HeaderLabelInfo | null>(null)
  const [showLabelsPage, setShowLabelsPage] = useState(false)
  const [availableLabels, setAvailableLabels] = useState<string[]>([])
  const [selectedLabelFilter, setSelectedLabelFilter] = useState('')
  const [labelRows, setLabelRows] = useState<LabelInfoRow[]>([])
  const [labelLoading, setLabelLoading] = useState(false)
  const [availableFiles, setAvailableFiles] = useState<string[]>([])
  const [selectedFileFilter, setSelectedFileFilter] = useState('')

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) {
      const validTypes = ['text/csv', 'application/vnd.ms-excel', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet']
      const fileExtension = file.name.toLowerCase().split('.').pop()
      
      if (!validTypes.includes(file.type) && !['csv', 'xlsx', 'xls'].includes(fileExtension || '')) {
        const message = 'Please select a valid CSV or Excel file'
        setUploadError(message)
        toast.error(message)
        setUploadFile(null)
        return
      }
      
      setUploadFile(file)
      setUploadError(null)
    }
  }

  const handleUpload = async () => {
    if (!uploadFile) {
      const message = 'Please select a file first'
      setUploadError(message)
      toast.error(message)
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
      
      const csvResult = result.label_csv
      const messages: string[] = []
      if (csvResult?.rows_added > 0) {
        messages.push(`${csvResult.rows_added} new header label${csvResult.rows_added === 1 ? '' : 's'} saved`)
      }
      if (csvResult?.rows_updated > 0) {
        messages.push(`${csvResult.rows_updated} existing header label${csvResult.rows_updated === 1 ? '' : 's'} updated`)
      }
      if (messages.length === 0) {
        messages.push('No label metadata changes were needed')
      }
      toast.success(`File uploaded successfully. ${messages.join('. ')}`)
      
      // Clear the file input
      const fileInput = document.getElementById('file-input') as HTMLInputElement
      if (fileInput) fileInput.value = ''
    } catch (err) {
      const message = err instanceof Error ? err.message : 'An error occurred during upload'
      setUploadError(message)
      toast.error(message)
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

  useEffect(() => {
    const handleOutsideClick = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setDropdownOpen(false)
      }
    }

    document.addEventListener('mousedown', handleOutsideClick)
    return () => document.removeEventListener('mousedown', handleOutsideClick)
  }, [])

  const handleHeaderSelect = (header: string) => {
    setSelectedHeader(header)
    setCurrentPage(1)
    setData(null)
    setDropdownOpen(false)
    fetchData(header, 1)
  }

  const handleExportHeaders = async (format: 'csv' | 'excel') => {
    if (!fileStatus.has_file) {
      const message = 'No file uploaded'
      setExportError(message)
      toast.error(message)
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
      const successMessage = `Headers exported successfully to ${result.output_file}`
      setExportSuccess(successMessage)
      toast.success(successMessage)
    } catch (err) {
      const message = err instanceof Error ? err.message : 'An error occurred during export'
      setExportError(message)
      toast.error(message)
    } finally {
      setExporting(false)
    }
  }

  const handleManualTextSave = async () => {
    if (!manualText.trim()) {
      const message = 'Please enter text to classify'
      setManualError(message)
      toast.error(message)
      return
    }

    try {
      setManualSaving(true)
      setManualError(null)
      setManualResult(null)

      const response = await fetch('http://localhost:8000/api/classify-text', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ text: manualText.trim() })
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || 'Manual text save failed')
      }

      const result = await response.json()
      setManualResult(result.label_info)
      toast.success('Text labeled and saved successfully')
      setManualText('')
    } catch (err) {
      const message = err instanceof Error ? err.message : 'An error occurred while saving text'
      setManualError(message)
      toast.error(message)
    } finally {
      setManualSaving(false)
    }
  }

  const fetchLabelInfo = async (label = selectedLabelFilter, file = selectedFileFilter) => {
    try {
      setLabelLoading(true)
      const params = new URLSearchParams()
      if (label) params.append('label', label)
      if (file) params.append('file', file)
      const url = `http://localhost:8000/api/labels?${params.toString()}`
      const response = await fetch(url)
      if (!response.ok) {
        const errorData = await response.json().catch(() => null)
        throw new Error(errorData?.detail || 'Failed to load label info')
      }
      const result = await response.json()
      setLabelRows(result.rows)
      setAvailableLabels(result.label_options)
      setAvailableFiles(result.file_options || [])
      setSelectedLabelFilter(result.selected_label || '')
      setSelectedFileFilter(result.selected_file || '')
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to load label info'
      toast.error(message)
    } finally {
      setLabelLoading(false)
    }
  }

  const handleLabelFilterChange = async (selectedLabel: string) => {
    setSelectedLabelFilter(selectedLabel)
    await fetchLabelInfo(selectedLabel, selectedFileFilter)
  }

  const handleFileFilterChange = async (selectedFile: string) => {
    setSelectedFileFilter(selectedFile)
    await fetchLabelInfo(selectedLabelFilter, selectedFile)
  }

  const handleExportLabelInfo = async (format: 'csv' | 'excel' = 'csv') => {
    try {
      setLabelLoading(true)
      const params = new URLSearchParams()
      if (selectedLabelFilter) params.append('label', selectedLabelFilter)
      if (selectedFileFilter) params.append('file', selectedFileFilter)
      params.append('format', format)

      const response = await fetch(`http://localhost:8000/api/labels/export?${params.toString()}`)
      if (!response.ok) {
        const errorData = await response.json().catch(() => null)
        throw new Error(errorData?.detail || 'Failed to export label info')
      }
      const blob = await response.blob()
      const downloadUrl = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = downloadUrl
      const filename = response.headers.get('content-disposition')?.split('filename=')[1] ?? `label_info.${format === 'excel' ? 'xlsx' : 'csv'}`
      link.download = filename.replace(/"/g, '')
      document.body.appendChild(link)
      link.click()
      link.remove()
      window.URL.revokeObjectURL(downloadUrl)
      toast.success('Label info exported successfully')
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to export label info'
      toast.error(message)
    } finally {
      setLabelLoading(false)
    }
  }

  return (
    <div style={{ maxWidth: 1000, margin: '2rem auto', fontFamily: 'Arial, sans-serif', padding: '1rem' }}>
      <h1>CSV/Excel Data Manager</h1>

      <ToastContainer position="top-right" autoClose={4000} hideProgressBar={false} newestOnTop closeOnClick pauseOnHover />

      <div style={{ marginBottom: '1rem' }}>
        <button
          type="button"
          onClick={() => {
            setShowLabelsPage(false)
            setSelectedLabelFilter('')
            setLabelRows([])
          }}
          style={{
            marginRight: '0.75rem',
            padding: '0.75rem 1rem',
            backgroundColor: '#1976D2',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            cursor: 'pointer'
          }}
        >
          Main Page
        </button>
        <button
          type="button"
          onClick={async () => {
            setShowLabelsPage(true)
            await fetchLabelInfo()
          }}
          style={{
            padding: '0.75rem 1rem',
            backgroundColor: '#4CAF50',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            cursor: 'pointer'
          }}
        >
          Label Info Page
        </button>
      </div>

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

        <div style={{ marginTop: '1.5rem', padding: '1rem', backgroundColor: '#ffffff', borderRadius: '8px', border: '1px solid #ddd' }}>
          <h3 style={{ margin: 0, marginBottom: '0.75rem' }}>Manual Text Label</h3>
          <p style={{ margin: 0, marginBottom: '0.75rem', color: '#666' }}>
            Enter a custom label text. The system will classify whether it indicates Age and save it to <code>label_info.csv</code>.
          </p>
          <textarea
            value={manualText}
            onChange={(e) => setManualText(e.target.value)}
            rows={4}
            placeholder="Enter text to classify and save"
            style={{
              width: '100%',
              padding: '0.75rem',
              border: '1px solid #ccc',
              borderRadius: '4px',
              resize: 'vertical',
              fontSize: '1rem',
              minHeight: '100px'
            }}
          />
          <button
            onClick={handleManualTextSave}
            disabled={manualSaving}
            style={{
              marginTop: '0.75rem',
              padding: '0.75rem 1.5rem',
              backgroundColor: manualSaving ? '#cccccc' : '#1976D2',
              color: 'white',
              border: 'none',
              borderRadius: '4px',
              cursor: manualSaving ? 'not-allowed' : 'pointer',
              fontSize: '1rem',
              fontWeight: 'bold'
            }}
          >
            {manualSaving ? 'Saving...' : 'Save Text Label'}
          </button>

          {manualError && (
            <div style={{ marginTop: '1rem', padding: '1rem', backgroundColor: '#ffebee', color: '#c62828', borderRadius: '4px', border: '1px solid #ef5350' }}>
              <strong>Error:</strong> {manualError}
            </div>
          )}

          {manualResult && (
            <div style={{ marginTop: '1rem', padding: '1rem', backgroundColor: '#e8f5e9', color: '#2e7d32', borderRadius: '4px', border: '1px solid #4caf50' }}>
              <p style={{ margin: '0.25rem 0' }}><strong>Label:</strong> {manualResult.label}</p>
              <p style={{ margin: '0.25rem 0' }}><strong>Reason:</strong> {manualResult.reason}</p>
              <p style={{ margin: '0.25rem 0' }}><strong>Saved Text:</strong> {manualResult.header_text}</p>
              <p style={{ margin: '0.25rem 0' }}><strong>File Name:</strong> {manualResult.filename}</p>
            </div>
          )}
        </div>

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

      {showLabelsPage ? (
        <div style={{ backgroundColor: '#eef3ff', padding: '1.5rem', borderRadius: '8px', border: '1px solid #b3c7ff' }}>
          <h2 style={{ marginTop: 0 }}>Label Info</h2>
          <div style={{ marginBottom: '1rem', display: 'flex', flexWrap: 'wrap', gap: '0.75rem', alignItems: 'center' }}>
            <label style={{ fontWeight: 'bold' }} htmlFor="label-filter">Filter by label:</label>
            <select
              id="label-filter"
              value={selectedLabelFilter}
              onChange={(e) => handleLabelFilterChange(e.target.value)}
              style={{ padding: '0.75rem', border: '1px solid #ccc', borderRadius: '4px', minWidth: '180px' }}
            >
              <option value="">All labels</option>
              {availableLabels.map((option) => (
                <option key={option} value={option}>{option}</option>
              ))}
            </select>

            <label style={{ fontWeight: 'bold' }} htmlFor="file-filter">Filter by file:</label>
            <select
              id="file-filter"
              value={selectedFileFilter}
              onChange={(e) => handleFileFilterChange(e.target.value)}
              style={{ padding: '0.75rem', border: '1px solid #ccc', borderRadius: '4px', minWidth: '180px' }}
            >
              <option value="">All files</option>
              {availableFiles.map((f) => (
                <option key={f} value={f}>{f}</option>
              ))}
            </select>

            <button
              type="button"
              onClick={() => handleExportLabelInfo('csv')}
              disabled={labelLoading}
              style={{
                padding: '0.75rem 1.25rem',
                backgroundColor: '#FF9800',
                color: 'white',
                border: 'none',
                borderRadius: '4px',
                cursor: 'pointer'
              }}
            >
              Export CSV
            </button>

            <button
              type="button"
              onClick={() => handleExportLabelInfo('excel')}
              disabled={labelLoading}
              style={{
                padding: '0.75rem 1.25rem',
                backgroundColor: '#1976D2',
                color: 'white',
                border: 'none',
                borderRadius: '4px',
                cursor: 'pointer'
              }}
            >
              Export Excel
            </button>
          </div>

          {labelLoading ? (
            <p style={{ color: '#666' }}>Loading label info...</p>
          ) : labelRows.length === 0 ? (
            <div style={{ padding: '1rem', backgroundColor: 'white', borderRadius: '8px', border: '1px solid #ddd' }}>
              <p style={{ margin: 0, color: '#666' }}>No label metadata found.</p>
            </div>
          ) : (
            <div style={{ overflowX: 'auto', backgroundColor: 'white', borderRadius: '8px', border: '1px solid #ddd' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead>
                  <tr style={{ backgroundColor: '#f5f7ff' }}>
                    <th style={{ padding: '0.75rem', textAlign: 'left', borderBottom: '2px solid #ddd' }}>Label</th>
                    <th style={{ padding: '0.75rem', textAlign: 'left', borderBottom: '2px solid #ddd' }}>Header Text</th>
                    <th style={{ padding: '0.75rem', textAlign: 'left', borderBottom: '2px solid #ddd' }}>File Name</th>
                    <th style={{ padding: '0.75rem', textAlign: 'left', borderBottom: '2px solid #ddd' }}>Header Index</th>
                  </tr>
                </thead>
                <tbody>
                  {labelRows.map((row, index) => (
                    <tr key={`${row['file name']}-${row['header text']}-${index}`} style={{ backgroundColor: index % 2 === 0 ? '#fafbff' : 'white' }}>
                      <td style={{ padding: '0.75rem', borderBottom: '1px solid #eee' }}>{row.Label}</td>
                      <td style={{ padding: '0.75rem', borderBottom: '1px solid #eee' }}>{row['header text']}</td>
                      <td style={{ padding: '0.75rem', borderBottom: '1px solid #eee' }}>{row['file name']}</td>
                      <td style={{ padding: '0.75rem', borderBottom: '1px solid #eee' }}>{row['header index']}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      ) : (
        fileStatus.has_file && (
          <div style={{ 
            backgroundColor: '#f0f5ff', 
            padding: '1.5rem', 
            borderRadius: '8px',
            border: '1px solid #b3d9ff'
          }}>
            <h2 style={{ marginTop: 0 }}>Data Viewer</h2>
            
            <div style={{ marginBottom: '1.5rem' }}>
              <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 'bold' }}>
                Select a column header:
              </label>
              <div ref={dropdownRef} style={{ position: 'relative', width: '100%', maxWidth: '100%', minWidth: 0 }}>
                <button
                  type="button"
                  onClick={() => setDropdownOpen((open) => !open)}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    width: '100%',
                    boxSizing: 'border-box',
                    padding: '0.75rem',
                    fontSize: '1rem',
                    borderRadius: '4px',
                    border: '1px solid #ccc',
                    backgroundColor: 'white',
                    cursor: 'pointer',
                    color: '#111',
                    minHeight: '3.5rem',
                    lineHeight: '1.4',
                    whiteSpace: 'normal',
                    wordBreak: 'break-word',
                    overflowWrap: 'anywhere'
                  }}
                >
                  <span style={{ display: 'block', minWidth: 0, wordBreak: 'break-word', whiteSpace: 'normal', overflowWrap: 'anywhere' }}>
                    {selectedHeader || '-- Select a header --'}
                  </span>
                  <span style={{ marginLeft: '1rem', flexShrink: 0 }}>
                    ▼
                  </span>
                </button>

                {dropdownOpen && (
                  <div style={{
                    position: 'absolute',
                    top: '100%',
                    left: 0,
                    width: '100%',
                    zIndex: 1000,
                    maxHeight: '240px',
                    overflowY: 'auto',
                    marginTop: '0.5rem',
                    border: '1px solid #ccc',
                    borderRadius: '4px',
                    backgroundColor: 'white',
                    boxShadow: '0 8px 16px rgba(0,0,0,0.12)',
                    boxSizing: 'border-box'
                  }}>
                    {fileStatus.headers.map((header) => (
                      <button
                        key={header}
                        type="button"
                        onClick={() => handleHeaderSelect(header)}
                        onMouseDown={(e) => e.preventDefault()}
                        style={{
                          display: 'block',
                          width: '100%',
                          boxSizing: 'border-box',
                          textAlign: 'left',
                          padding: '0.75rem',
                          background: selectedHeader === header ? '#f0f4ff' : 'white',
                          border: 'none',
                          borderBottom: '1px solid #eee',
                          cursor: 'pointer',
                          color: '#111',
                          whiteSpace: 'normal',
                          wordBreak: 'break-word',
                          overflowWrap: 'anywhere'
                        }}
                      >
                        {header}
                      </button>
                    ))}
                  </div>
                )}
              </div>
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
        )
      )}
    </div>
  )
}

export default App
