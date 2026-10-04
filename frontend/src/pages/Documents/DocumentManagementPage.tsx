import { useState } from "react";
import DocumentUpload from "../../components/documents/DocumentUpload";
import DocumentList from "../../components/documents/DocumentList";

function DocumentManagementPage() {
  const [refreshKey, setRefreshKey] =
    useState(0);

  const handleUploadSuccess = () => {
    setRefreshKey((prev) => prev + 1);
  };

  return (
    <div style={{ paddingBottom: "32px" }}>
      <div className="page-header">
        <div>
          <h2>Quản lý tài liệu</h2>
          <p>
            Tải lên và quản lý tài liệu hệ thống.
          </p>
        </div>
      </div>

      <DocumentUpload
        onUploadSuccess={
          handleUploadSuccess
        }
      />

      <DocumentList
        refreshKey={refreshKey}
      />
    </div>
  );
}

export default DocumentManagementPage;