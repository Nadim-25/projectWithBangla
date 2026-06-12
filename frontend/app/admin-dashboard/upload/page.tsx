"use client";

import { useRef, useState } from "react";

import { Upload, FileText, Loader2, X, CloudUpload } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { BASE_URL } from "@/settings";

const MAX_FILE_SIZE = 10 * 1024 * 1024;

const ALLOWED_TYPES = [
  "application/pdf",
  "application/msword",
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
];

export default function UploadPage() {
  const [file, setFile] = useState<File | null>(null);

  const [displayName, setDisplayName] = useState("");

  const [division, setDivision] = useState("SME");

  const [department, setDepartment] = useState("CRM");

  const [loading, setLoading] = useState(false);

  const [dragActive, setDragActive] = useState(false);

  const inputRef = useRef<HTMLInputElement | null>(null);

  // =========================
  // VALIDATE FILE
  // =========================
  const validateFile = (selectedFile: File) => {
    // type validation
    if (!ALLOWED_TYPES.includes(selectedFile.type)) {
      alert("Only PDF, DOC, DOCX files allowed");
      return false;
    }

    // size validation
    if (selectedFile.size > MAX_FILE_SIZE) {
      alert("File size exceeds 10MB");
      return false;
    }

    return true;
  };

  // =========================
  // FILE CHANGE
  // =========================
  const handleFileChange = (selectedFile: File | null) => {
    if (!selectedFile) return;

    const valid = validateFile(selectedFile);

    if (!valid) return;

    setFile(selectedFile);

    // auto set display name
    const name = selectedFile.name.split(".")[0];

    setDisplayName(name);
  };

  // =========================
  // DRAG EVENTS
  // =========================
  const handleDragOver = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setDragActive(true);
  };

  const handleDragLeave = () => {
    setDragActive(false);
  };

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();

    setDragActive(false);

    const droppedFile = e.dataTransfer.files?.[0];

    if (droppedFile) {
      handleFileChange(droppedFile);
    }
  };

  // =========================
  // GET TOKEN
  // =========================
  const getToken = () => {
    return document.cookie
      .split("; ")
      .find((row) => row.startsWith("token="))
      ?.split("=")[1];
  };

  // =========================
  // UPLOAD
  // =========================
  const handleUpload = async () => {
    if (!file) return;

    try {
      setLoading(true);

      const token = getToken();

      const formData = new FormData();

      formData.append("file", file);

      formData.append("displayName", displayName);

      formData.append("division", division);

      formData.append("department", department);

      const res = await fetch(`${BASE_URL}/upload`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
        },
        body: formData,
      });

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.detail || "Upload failed");
      }

      alert("Uploaded successfully");

      // reset
      setFile(null);
      setDisplayName("");
    } catch (err: any) {
      console.error(err);

      alert(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-6 p-6">
      {/* HEADER */}
      <div>
        <h1 className="text-3xl font-bold">Upload Document</h1>

        <p className="mt-2 text-muted-foreground">
          Upload PDF or Word documents.
        </p>
      </div>

      <Card className="p-6">
        {/* DISPLAY NAME */}
        <div className="mb-4">
          <label className="mb-2 block text-sm font-medium">Display Name</label>

          <Input
            value={displayName}
            onChange={(e) => setDisplayName(e.target.value)}
            placeholder="Document title"
          />
        </div>

        {/* DRAG AREA */}
        <div
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={() => inputRef.current?.click()}
          className={`flex min-h-[220px] cursor-pointer flex-col items-center justify-center rounded-2xl border-2 border-dashed transition-all ${
            dragActive
              ? "border-primary bg-primary/5"
              : "border-muted-foreground/25 hover:border-primary hover:bg-muted/40"
          }`}
        >
          <div className="mb-4 rounded-full bg-muted p-4">
            <CloudUpload className="h-10 w-10 text-muted-foreground" />
          </div>

          <h2 className="text-lg font-semibold">Drag & Drop your file here</h2>

          <p className="mt-2 text-sm text-muted-foreground">
            or click to browse
          </p>

          <p className="mt-4 text-xs text-muted-foreground">
            PDF, DOC, DOCX (max 5MB)
          </p>

          <input
            ref={inputRef}
            type="file"
            accept=".pdf,.doc,.docx"
            className="hidden"
            onChange={(e) => handleFileChange(e.target.files?.[0] || null)}
          />
        </div>

        {/* FILE PREVIEW */}
        {file && (
          <div className="mt-6 flex items-center justify-between rounded-xl border bg-muted/40 p-4">
            <div className="flex items-center gap-3">
              <div className="rounded-lg bg-background p-2">
                <FileText className="h-5 w-5" />
              </div>

              <div>
                <p className="text-sm font-medium">{file.name}</p>

                <p className="text-xs text-muted-foreground">
                  {(file.size / 1024 / 1024).toFixed(2)} MB
                </p>
              </div>
            </div>

            <Button variant="ghost" size="icon" onClick={() => setFile(null)}>
              <X className="h-4 w-4" />
            </Button>
          </div>
        )}

        {/* ACTION */}
        <div className="mt-6 flex justify-end">
          <Button disabled={!file || loading} onClick={handleUpload}>
            {loading ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Uploading...
              </>
            ) : (
              <>
                <Upload className="mr-2 h-4 w-4" />
                Upload File
              </>
            )}
          </Button>
        </div>
      </Card>
    </div>
  );
}
