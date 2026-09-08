import DocumentUpload from "../../components/documents/DocumentUpload";

function DocumentManagementPage() {
  return (
    <div>
      <div className="page-header">
        <div>
          <h2>Quản lý tài liệu</h2>
          <p>Tải tài liệu hệ thống.</p>
        </div>
      </div>

      <DocumentUpload />
    </div>
  );
}

export default DocumentManagementPage;