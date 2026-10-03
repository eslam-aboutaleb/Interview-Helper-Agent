import React, { useRef, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { FileText, Trash2, Upload } from 'lucide-react';
import { DocumentType, documentsApi, parseAxiosError } from '../services/api';
import { ErrorResponse } from '../services/errorHandler';
import Alert from '../components/Alert';
import EmptyState from '../components/EmptyState';
import { Skeleton } from '../components/ui/Skeleton';
import { Button } from '../components/ui/Button';
import { Badge } from '../components/ui/Badge';
import { UserDocument } from '../types';

const DOCUMENTS_QUERY_KEY = ['documents'];

interface UploadPanelProps {
  documentType: DocumentType;
  title: string;
  hint: string;
  onUploaded: () => void;
}

const UploadPanel: React.FC<UploadPanelProps> = ({ documentType, title, hint, onUploaded }) => {
  const inputRef = useRef<HTMLInputElement>(null);
  const [error, setError] = useState<string | null>(null);

  const upload = useMutation({
    mutationFn: (file: File) => documentsApi.upload(documentType, file),
    onSuccess: () => {
      setError(null);
      if (inputRef.current) {
        inputRef.current.value = '';
      }
      onUploaded();
    },
    onError: (err) => {
      setError(parseAxiosError(err).message);
    },
  });

  const handleChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      upload.mutate(file);
    }
  };

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-6">
      <h3 className="text-lg font-semibold text-gray-900">{title}</h3>
      <p className="mt-1 text-sm text-gray-500">{hint}</p>

      <div className="mt-4 flex items-center gap-3">
        <input
          ref={inputRef}
          type="file"
          accept=".pdf,.docx,.txt"
          onChange={handleChange}
          className="hidden"
          aria-label={`Upload ${title}`}
        />
        <Button
          onClick={() => inputRef.current?.click()}
          isLoading={upload.isPending}
          variant="primary"
          size="md"
        >
          <Upload className="w-4 h-4 mr-2" />
          {upload.isPending ? 'Uploading...' : 'Choose file'}
        </Button>
        <span className="text-xs text-gray-400">PDF, DOCX or TXT</span>
      </div>

      {error && (
        <div className="mt-4">
          <Alert type="error" title="Upload failed" message={error} />
        </div>
      )}
    </div>
  );
};

const Documents: React.FC = () => {
  const queryClient = useQueryClient();

  const {
    data: documents = [],
    isLoading,
    isError,
    error,
  } = useQuery<UserDocument[]>({
    queryKey: DOCUMENTS_QUERY_KEY,
    queryFn: () => documentsApi.list().then((r) => r.data),
  });

  const remove = useMutation({
    mutationFn: (documentId: number) => documentsApi.remove(documentId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: DOCUMENTS_QUERY_KEY });
    },
  });

  const listError: ErrorResponse | null = remove.isError ? parseAxiosError(remove.error) : null;

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Skeleton width={240} height={36} />
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {[0, 1].map((i) => (
            <Skeleton key={i} width="100%" height={140} variant="rectangular" />
          ))}
        </div>
        <Skeleton width="100%" height={220} variant="rectangular" />
      </div>
    );
  }

  const queryError: ErrorResponse | null = isError ? parseAxiosError(error) : null;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Documents</h1>
        <p className="mt-2 text-gray-600">
          Upload your resume and job descriptions to power skill-gap analysis.
        </p>
      </div>

      {queryError && (
        <Alert type="error" title="Failed to load documents" message={queryError.message} />
      )}

      {listError && (
        <Alert type="error" title="Failed to delete document" message={listError.message} />
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <UploadPanel
          documentType="resume"
          title="Resume"
          hint="Your most recent resume. Required for skill-gap analysis."
          onUploaded={() => queryClient.invalidateQueries({ queryKey: DOCUMENTS_QUERY_KEY })}
        />
        <UploadPanel
          documentType="jd"
          title="Job description"
          hint="Paste the target role's description to compare against."
          onUploaded={() => queryClient.invalidateQueries({ queryKey: DOCUMENTS_QUERY_KEY })}
        />
      </div>

      {documents.length === 0 ? (
        <EmptyState
          title="No documents yet"
          message="Upload a resume and a job description to get started."
          icon={<FileText className="w-12 h-12 text-gray-400" />}
        />
      ) : (
        <div className="bg-white rounded-lg border border-gray-200 divide-y divide-gray-100">
          {documents.map((doc) => (
            <div key={doc.id} className="flex items-center justify-between p-4">
              <div className="flex items-center gap-3 min-w-0">
                <FileText className="w-5 h-5 text-gray-400 shrink-0" />
                <div className="min-w-0">
                  <p className="font-medium text-gray-900 truncate">{doc.filename || 'Untitled'}</p>
                  <p className="text-xs text-gray-500">
                    Uploaded {new Date(doc.created_at).toLocaleString()}
                  </p>
                </div>
                <Badge variant={doc.document_type === 'resume' ? 'primary' : 'neutral'}>
                  {doc.document_type === 'resume' ? 'Resume' : 'Job description'}
                </Badge>
              </div>
              <Button
                onClick={() => remove.mutate(doc.id)}
                disabled={remove.isPending}
                variant="ghost"
                size="sm"
                aria-label={`Delete ${doc.filename || 'document'}`}
              >
                <Trash2 className="w-4 h-4" />
              </Button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default Documents;
