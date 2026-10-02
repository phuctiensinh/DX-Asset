'use client';

import React, { useState, useEffect, useCallback } from 'react';
import Link from 'next/link';
import { useAuth } from '@/lib/auth-context';
import { ProtectedRoute } from '@/components/ProtectedRoute';
import { Navbar } from '@/components/Navbar';
import { fetchApi, uploadIncidentAttachment, deleteIncidentAttachment, getIncidentAttachmentFileUrl, fetchAttachmentBlob } from '@/lib/api';

import {
  AlertTriangle,
  Plus,
  Search,
  Filter,
  X,
  Loader2,
  AlertCircle,
  CheckCircle2,
  User as UserIcon,
  Calendar,
  Wrench,
  Boxes,
  Eye,
  Edit3,
  DollarSign,
  Clock,
  ShieldAlert,
  Sparkles,
  Cpu,
  Layers,
  UserCheck,
  BookOpen,
  Paperclip,
  Upload,
  FileText,
  Trash2,
  Download,
  Image as ImageIcon,
  Camera,
} from 'lucide-react';


interface AssetSummary {
  id: number;
  asset_code: string;
  name: string;
  category: string;
  status: string;
}

interface UserSummary {
  id: number;
  email: string;
  full_name: string;
  role: string;
}

export interface IncidentAttachment {
  id: number;
  incident_id: number;
  file_name: string;
  file_size: number;
  mime_type: string;
  uploaded_by_id: number;
  created_at: string;
  file_url: string;
}

interface Incident {
  id: number;
  ticket_code: string;
  asset_id: number;
  reporter_id: number;
  title: string;
  description: string;
  category: string;
  priority: string;
  status: string;
  assigned_it_id?: number | null;
  resolution_notes?: string | null;
  repair_cost: number;
  suggested_queue?: string | null;
  ai_confidence?: number | null;
  ai_reasoning?: string | null;
  created_at: string;
  updated_at: string;
  resolved_at?: string | null;
  asset?: AssetSummary | null;
  reporter?: UserSummary | null;
  assigned_it?: UserSummary | null;
  attachments?: IncidentAttachment[];
}


interface TechnicianRecommendationItem {
  user_id: number;
  full_name: string;
  email: string;
  role: string;
  total_score: number;
  skill_score: number;
  workload_score: number;
  sla_score: number;
  active_workload: number;
  reasons: string[];
}

interface RecommendationsResponse {
  incident_id: number;
  ticket_code: string;
  category: string;
  priority: string;
  suggested_queue: string;
  recommendations: TechnicianRecommendationItem[];
}

interface LinkedMaintenanceInfo {
  maintenance_code: string;
  status: string;
  repair_cost: number;
  duration_hours?: number | null;
  resolution_notes?: string | null;
}

interface SimilarIncidentItem {
  incident_id: number;
  ticket_code: string;
  title: string;
  category: string;
  priority: string;
  status: string;
  resolution_notes: string;
  repair_cost: number;
  resolved_at?: string | null;
  asset_code?: string | null;
  asset_name?: string | null;
  similarity_score: number;
  similarity_reasons: string[];
  linked_maintenance?: LinkedMaintenanceInfo | null;
}

interface SimilarIncidentListResponse {
  target_incident_id: number;
  target_ticket_code: string;
  total_found: number;
  items: SimilarIncidentItem[];
}

interface IncidentListResponse {
  items: Incident[];
  total: number;
  skip: number;
  limit: number;
}

interface AssetListResponse {
  items: AssetSummary[];
  total: number;
}

const VALID_STATUS_TRANSITIONS: Record<string, { value: string; label: string }[]> = {
  OPEN: [
    { value: 'OPEN', label: 'Mới tạo (OPEN)' },
    { value: 'IN_REVIEW', label: 'Đang xem xét (IN_REVIEW)' },
    { value: 'IN_PROGRESS', label: 'Đang xử lý (IN_PROGRESS)' },
    { value: 'CANCELLED', label: 'Đã hủy (CANCELLED)' },
  ],
  IN_REVIEW: [
    { value: 'IN_REVIEW', label: 'Đang xem xét (IN_REVIEW)' },
    { value: 'IN_PROGRESS', label: 'Đang xử lý (IN_PROGRESS)' },
    { value: 'WAITING_FOR_INFO', label: 'Chờ thông tin (WAITING_FOR_INFO)' },
    { value: 'RESOLVED', label: 'Đã khắc phục (RESOLVED)' },
    { value: 'CANCELLED', label: 'Đã hủy (CANCELLED)' },
  ],
  IN_PROGRESS: [
    { value: 'IN_PROGRESS', label: 'Đang xử lý (IN_PROGRESS)' },
    { value: 'WAITING_FOR_INFO', label: 'Chờ thông tin (WAITING_FOR_INFO)' },
    { value: 'RESOLVED', label: 'Đã khắc phục (RESOLVED)' },
    { value: 'CANCELLED', label: 'Đã hủy (CANCELLED)' },
  ],
  WAITING_FOR_INFO: [
    { value: 'WAITING_FOR_INFO', label: 'Chờ thông tin (WAITING_FOR_INFO)' },
    { value: 'IN_PROGRESS', label: 'Đang xử lý (IN_PROGRESS)' },
    { value: 'RESOLVED', label: 'Đã khắc phục (RESOLVED)' },
    { value: 'CANCELLED', label: 'Đã hủy (CANCELLED)' },
  ],
  RESOLVED: [
    { value: 'RESOLVED', label: 'Đã khắc phục (RESOLVED)' },
    { value: 'CLOSED', label: 'Đã đóng (CLOSED)' },
    { value: 'IN_PROGRESS', label: 'Mở lại xử lý (IN_PROGRESS)' },
  ],
  CLOSED: [
    { value: 'CLOSED', label: 'Đã đóng (CLOSED - Không thể đổi)' },
  ],
  CANCELLED: [
    { value: 'CANCELLED', label: 'Đã hủy (CANCELLED - Không thể đổi)' },
  ],
};

function IncidentsContent() {
  const { user } = useAuth();
  const canManageIT = user?.role === 'ADMIN' || user?.role === 'IT_ASSET_MANAGER';

  // Data State
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [total, setTotal] = useState<number>(0);
  const [skip, setSkip] = useState<number>(0);
  const limit = 10;
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // Filters
  const [search, setSearch] = useState<string>('');
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [priorityFilter, setPriorityFilter] = useState<string>('');
  const [categoryFilter, setCategoryFilter] = useState<string>('');

  // Dropdowns reference data
  const [assetsList, setAssetsList] = useState<AssetSummary[]>([]);
  const [itUsersList, setItUsersList] = useState<UserSummary[]>([]);

  // Modals
  const [showCreateModal, setShowCreateModal] = useState<boolean>(false);
  const [showUpdateModal, setShowUpdateModal] = useState<boolean>(false);
  const [showDetailModal, setShowDetailModal] = useState<boolean>(false);
  const [showRecommendationModal, setShowRecommendationModal] = useState<boolean>(false);
  const [selectedIncident, setSelectedIncident] = useState<Incident | null>(null);

  // Smart Routing Recommendation State
  const [recommendationsData, setRecommendationsData] = useState<RecommendationsResponse | null>(null);
  const [loadingRecommendations, setLoadingRecommendations] = useState<boolean>(false);
  const [assigningTechId, setAssigningTechId] = useState<number | null>(null);

  const openRecommendationModal = async (inc: Incident) => {
    setSelectedIncident(inc);
    setShowRecommendationModal(true);
    setLoadingRecommendations(true);
    setRecommendationsData(null);
    try {
      const data = await fetchApi<RecommendationsResponse>(`/incidents/${inc.id}/recommendations`);
      setRecommendationsData(data);
    } catch (err: any) {
      console.error('Lỗi lấy đề xuất Kỹ thuật viên:', err);
    } finally {
      setLoadingRecommendations(false);
    }
  };

  const handleAssignTechnician = async (incidentId: number, techId: number) => {
    setAssigningTechId(techId);
    try {
      await fetchApi<Incident>(`/incidents/${incidentId}/assign`, {
        method: 'POST',
        body: JSON.stringify({ technician_id: techId }),
      });
      setShowRecommendationModal(false);
      setSuccessMsg('Đã xác nhận phân công Kỹ thuật viên thành công!');
      setTimeout(() => setSuccessMsg(null), 4000);
      loadIncidents();
    } catch (err: any) {
      alert(err?.message || 'Không thể phân công Kỹ thuật viên');
    } finally {
      setAssigningTechId(null);
    }
  };

  // Form States
  const [createFormData, setCreateFormData] = useState({
    asset_id: '',
    title: '',
    category: 'HARDWARE',
    priority: 'MEDIUM',
    description: '',
  });

  const [updateFormData, setUpdateFormData] = useState({
    status: 'IN_PROGRESS',
    assigned_it_id: '',
    resolution_notes: '',
    repair_cost: '0',
  });

  const [formSubmitting, setFormSubmitting] = useState<boolean>(false);
  const [formError, setFormError] = useState<string | null>(null);

  const loadIncidents = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams();
      params.append('skip', skip.toString());
      params.append('limit', limit.toString());

      if (search.trim()) params.append('search', search.trim());
      if (statusFilter) params.append('status', statusFilter);
      if (priorityFilter) params.append('priority', priorityFilter);
      if (categoryFilter) params.append('category', categoryFilter);

      const data = await fetchApi<IncidentListResponse>(`/incidents?${params.toString()}`);
      setIncidents(data.items);
      setTotal(data.total);
    } catch (err: any) {
      setError(err?.message || 'Không thể tải danh sách sự cố báo hỏng');
    } finally {
      setIsLoading(false);
    }
  }, [skip, search, statusFilter, priorityFilter, categoryFilter]);

  useEffect(() => {
    loadIncidents();
  }, [loadIncidents]);

  const loadReferenceData = async () => {
    try {
      const [assetsRes, usersRes] = await Promise.all([
        fetchApi<AssetListResponse>('/assets?limit=100'),
        fetchApi<UserSummary[]>('/users'),
      ]);
      setAssetsList(assetsRes.items || []);
      const itUsers = (usersRes || []).filter(
        (u) => u.role === 'ADMIN' || u.role === 'IT_ASSET_MANAGER'
      );
      setItUsersList(itUsers);
    } catch (err: any) {
      console.error('Lỗi nạp dữ liệu danh mục:', err);
    }
  };

  // Pending Attachments for Create Incident Modal

  const [pendingFiles, setPendingFiles] = useState<File[]>([]);
  const [uploadProgressMsg, setUploadProgressMsg] = useState<string | null>(null);
  const createCameraInputRef = React.useRef<HTMLInputElement>(null);
  const createFilePickerInputRef = React.useRef<HTMLInputElement>(null);

  const ALLOWED_EXTS = ['.jpg', '.jpeg', '.png', '.webp', '.pdf', '.docx', '.xlsx'];
  const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10 MB

  const handleAddPendingFiles = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selected = Array.from(e.target.files || []);
    if (!selected.length) return;

    if (pendingFiles.length + selected.length > 5) {
      alert('Mỗi phiếu sự cố chỉ được đính kèm tối đa 5 tập tin.');
      if (e.target) e.target.value = '';
      return;
    }

    const invalidFiles: string[] = [];
    const validFiles: File[] = [];

    for (const f of selected) {
      const ext = '.' + f.name.split('.').pop()?.toLowerCase();
      if (!ALLOWED_EXTS.includes(ext)) {
        invalidFiles.push(`${f.name} (Định dạng '${ext}' không hỗ trợ)`);
        continue;
      }
      if (f.size > MAX_FILE_SIZE) {
        invalidFiles.push(`${f.name} (Dung lượng ${(f.size / (1024 * 1024)).toFixed(1)}MB vượt quá 10MB)`);
        continue;
      }
      validFiles.push(f);
    }

    if (invalidFiles.length > 0) {
      alert(`Một số tệp không hợp lệ và đã bị bỏ qua:\n- ${invalidFiles.join('\n- ')}`);
    }

    if (validFiles.length > 0) {
      setPendingFiles((prev) => [...prev, ...validFiles]);
    }

    if (e.target) e.target.value = '';
  };

  const handleRemovePendingFile = (index: number) => {
    setPendingFiles((prev) => prev.filter((_, i) => i !== index));
  };

  const openCreateModal = () => {
    loadReferenceData();
    setCreateFormData({
      asset_id: '',
      title: '',
      category: 'HARDWARE',
      priority: 'MEDIUM',
      description: '',
    });
    setPendingFiles([]);
    setUploadProgressMsg(null);
    setFormError(null);
    setShowCreateModal(true);
  };

  const openUpdateModal = (inc: Incident) => {
    loadReferenceData();
    setSelectedIncident(inc);
    setUpdateFormData({
      status: inc.status,
      assigned_it_id: inc.assigned_it_id ? inc.assigned_it_id.toString() : '',
      resolution_notes: inc.resolution_notes || '',
      repair_cost: inc.repair_cost ? inc.repair_cost.toString() : '0',
    });
    setFormError(null);
    setShowUpdateModal(true);
  };

  // Knowledge Base & Attachments State
  const [similarIncidents, setSimilarIncidents] = useState<SimilarIncidentListResponse | null>(null);
  const [loadingSimilar, setLoadingSimilar] = useState<boolean>(false);
  const [attachmentsList, setAttachmentsList] = useState<IncidentAttachment[]>([]);
  const [previewBlobs, setPreviewBlobs] = useState<Record<number, string>>({});
  const [uploadingAttachment, setUploadingAttachment] = useState<boolean>(false);
  const fileInputRef = React.useRef<HTMLInputElement>(null);

  const loadAttachments = async (incidentId: number) => {
    try {
      const data = await fetchApi<IncidentAttachment[]>(`/incidents/${incidentId}/attachments`);
      setAttachmentsList(data || []);

      if (data && data.length > 0) {
        data.forEach(async (att) => {
          if (att.mime_type.startsWith('image/')) {
            try {
              const { blobUrl } = await fetchAttachmentBlob(incidentId, att.id);
              setPreviewBlobs((prev) => ({ ...prev, [att.id]: blobUrl }));
            } catch (e) {
              console.error('Lỗi nạp ảnh đính kèm:', e);
            }
          }
        });
      }
    } catch (err: any) {
      console.error('Lỗi lấy tập tin đính kèm:', err);
    }
  };

  const handleDownloadAttachment = async (att: IncidentAttachment) => {
    if (!selectedIncident) return;
    try {
      const { blobUrl } = await fetchAttachmentBlob(selectedIncident.id, att.id);
      const a = document.createElement('a');
      a.href = blobUrl;
      a.download = att.file_name;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      setTimeout(() => URL.revokeObjectURL(blobUrl), 10000);
    } catch (err: any) {
      alert(err?.message || 'Không thể tải tập tin');
    }
  };

  const openDetailModal = async (inc: Incident) => {
    setSelectedIncident(inc);
    setShowDetailModal(true);
    setLoadingSimilar(true);
    setSimilarIncidents(null);
    setAttachmentsList(inc.attachments || []);
    loadAttachments(inc.id);
    try {
      const data = await fetchApi<SimilarIncidentListResponse>(`/incidents/${inc.id}/similar?limit=5`);
      setSimilarIncidents(data);
    } catch (err: any) {
      console.error('Lỗi lấy danh sách sự cố tương tự:', err);
    } finally {
      setLoadingSimilar(false);
    }
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || !selectedIncident) return;

    setUploadingAttachment(true);
    try {
      await uploadIncidentAttachment(selectedIncident.id, file);
      setSuccessMsg('Đã tải lên tập tin đính kèm thành công!');
      setTimeout(() => setSuccessMsg(null), 4000);
      loadAttachments(selectedIncident.id);
      loadIncidents();
    } catch (err: any) {
      alert(err?.message || 'Không thể tải lên tập tin đính kèm');
    } finally {
      setUploadingAttachment(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const handleDeleteAttachment = async (attachmentId: number) => {
    if (!selectedIncident || !confirm('Bạn có chắc chắn muốn xóa tập tin đính kèm này?')) return;
    try {
      await deleteIncidentAttachment(selectedIncident.id, attachmentId);
      setSuccessMsg('Đã xóa tập tin đính kèm!');
      setTimeout(() => setSuccessMsg(null), 4000);
      loadAttachments(selectedIncident.id);
      loadIncidents();
    } catch (err: any) {
      alert(err?.message || 'Không thể xóa tập tin đính kèm');
    }
  };

  const handleCreateSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);

    if (!createFormData.asset_id) {
      setFormError('Vui lòng chọn tài sản gặp sự cố.');
      return;
    }
    if (!createFormData.title.trim()) {
      setFormError('Vui lòng nhập tiêu đề sự cố.');
      return;
    }
    if (!createFormData.description.trim()) {
      setFormError('Vui lòng nhập chi tiết mô tả sự cố.');
      return;
    }

    setFormSubmitting(true);
    setUploadProgressMsg('Đang khởi tạo phiếu sự cố...');

    try {
      const createdIncident = await fetchApi<Incident>('/incidents', {
        method: 'POST',
        body: JSON.stringify({
          asset_id: parseInt(createFormData.asset_id),
          title: createFormData.title.trim(),
          category: createFormData.category,
          priority: createFormData.priority,
          description: createFormData.description.trim(),
        }),
      });

      let uploadedCount = 0;
      if (pendingFiles.length > 0) {
        for (let i = 0; i < pendingFiles.length; i++) {
          const file = pendingFiles[i];
          setUploadProgressMsg(`Đang tải lên tập tin đính kèm (${i + 1}/${pendingFiles.length}): ${file.name}...`);
          try {
            await uploadIncidentAttachment(createdIncident.id, file);
            uploadedCount++;
          } catch (attErr: any) {
            console.error(`Upload file ${file.name} failed:`, attErr);
            setFormError(
              `Đã tạo phiếu sự cố [${createdIncident.ticket_code}] thành công, nhưng không thể tải lên tệp "${file.name}": ${attErr?.message || 'Lỗi lưu trữ'}`
            );
            setFormSubmitting(false);
            setUploadProgressMsg(null);
            loadIncidents();
            return;
          }
        }
      }

      setShowCreateModal(false);
      const msg = uploadedCount > 0
        ? `Gửi báo cáo sự cố thành công kèm theo ${uploadedCount} tệp đính kèm!`
        : 'Gửi báo cáo sự cố thành công!';
      setSuccessMsg(msg);
      setTimeout(() => setSuccessMsg(null), 5000);
      loadIncidents();
    } catch (err: any) {
      setFormError(err?.message || 'Không thể gửi phiếu báo sự cố');
    } finally {
      setFormSubmitting(false);
      setUploadProgressMsg(null);
    }
  };

  const handleUpdateSubmit = async (e: React.FormEvent) => {

    e.preventDefault();
    if (!selectedIncident) return;
    setFormError(null);

    setFormSubmitting(true);
    try {
      await fetchApi<Incident>(`/incidents/${selectedIncident.id}`, {
        method: 'PATCH',
        body: JSON.stringify({
          status: updateFormData.status,
          assigned_it_id: updateFormData.assigned_it_id ? parseInt(updateFormData.assigned_it_id) : undefined,
          repair_cost: updateFormData.repair_cost ? parseFloat(updateFormData.repair_cost) : undefined,
        }),
      });
      setShowUpdateModal(false);
      setSuccessMsg('Cập nhật trạng thái sự cố thành công!');
      setTimeout(() => setSuccessMsg(null), 4000);
      loadIncidents();
    } catch (err: any) {
      setFormError(err?.message || 'Không thể cập nhật sự cố');
    } finally {
      setFormSubmitting(false);
    }
  };

  const getPriorityBadge = (priority: string) => {
    switch (priority) {
      case 'CRITICAL':
        return <span className="whitespace-nowrap inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-bold bg-rose-50 text-rose-700 border border-rose-200">Khẩn cấp</span>;
      case 'HIGH':
        return <span className="whitespace-nowrap inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-semibold bg-amber-50 text-amber-800 border border-amber-200">Cao</span>;
      case 'MEDIUM':
        return <span className="whitespace-nowrap inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-medium bg-sky-50 text-sky-700 border border-sky-200">Trung bình</span>;
      case 'LOW':
        return <span className="whitespace-nowrap inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-medium bg-slate-100 text-slate-700 border border-slate-200">Thấp</span>;
      default:
        return <span className="whitespace-nowrap inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-medium bg-slate-100 text-slate-700">{priority}</span>;
    }
  };

  const getStatusBadge = (statusStr: string) => {
    switch (statusStr) {
      case 'OPEN':
        return <span className="whitespace-nowrap inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-semibold bg-rose-50 text-rose-700 border border-rose-200">Mới tạo</span>;
      case 'IN_REVIEW':
        return <span className="whitespace-nowrap inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-semibold bg-purple-50 text-purple-700 border border-purple-200">Đang xem xét</span>;
      case 'IN_PROGRESS':
        return <span className="whitespace-nowrap inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-semibold bg-amber-50 text-amber-800 border border-amber-200 animate-pulse">Đang xử lý</span>;
      case 'WAITING_FOR_INFO':
        return <span className="whitespace-nowrap inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-semibold bg-sky-50 text-sky-700 border border-sky-200">Chờ thông tin</span>;
      case 'RESOLVED':
        return <span className="whitespace-nowrap inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">Đã khắc phục</span>;
      case 'CLOSED':
        return <span className="whitespace-nowrap inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-semibold bg-slate-100 text-slate-700 border border-slate-200">Đã đóng</span>;
      case 'CANCELLED':
        return <span className="whitespace-nowrap inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-semibold bg-zinc-100 text-zinc-600 border border-zinc-200">Đã hủy</span>;
      default:
        return <span className="whitespace-nowrap inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-semibold bg-slate-100 text-slate-700">{statusStr}</span>;
    }
  };

  const formatDate = (dateStr?: string | null) => {
    if (!dateStr) return '—';
    try {
      const d = new Date(dateStr);
      return d.toLocaleDateString('vi-VN', {
        month: '2-digit',
        day: '2-digit',
        year: 'numeric',
      });
    } catch {
      return dateStr;
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 text-slate-800 flex flex-col">
      <Navbar />

      <main className="flex-1 max-w-7xl w-full mx-auto p-4 sm:p-6 lg:p-8 space-y-6">
        {/* Page Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-white border border-slate-200/90 rounded-2xl p-6 shadow-sm">
          <div className="flex items-center space-x-3">
            <div className="w-11 h-11 rounded-xl bg-rose-50 border border-rose-100 flex items-center justify-center text-rose-600 shadow-sm">
              <AlertTriangle className="w-6 h-6" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-slate-900 tracking-tight">
                Quản lý Báo hỏng & Sự cố Kỹ thuật
              </h1>
              <p className="text-xs text-slate-500 mt-0.5">
                Tiếp nhận và xử lý sự cố thiết bị doanh nghiệp. Tổng số phiếu: <span className="font-semibold text-rose-600">{total}</span>
              </p>
            </div>
          </div>

          <button
            onClick={openCreateModal}
            className="flex items-center justify-center space-x-2 px-4 py-2.5 bg-rose-600 hover:bg-rose-700 text-white font-semibold text-xs rounded-xl shadow-md shadow-rose-600/20 transition-all"
          >
            <Plus className="w-4 h-4" />
            <span>+ Báo sự cố mới</span>
          </button>
        </div>

        {/* Global Notifications */}
        {successMsg && (
          <div className="p-4 rounded-xl bg-emerald-50 border border-emerald-200 text-emerald-800 text-sm flex items-center space-x-2 animate-fadeIn shadow-sm">
            <CheckCircle2 className="w-5 h-5 flex-shrink-0 text-emerald-600" />
            <span>{successMsg}</span>
          </div>
        )}

        {error && (
          <div className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 text-sm flex items-center space-x-2 shadow-sm">
            <AlertCircle className="w-5 h-5 flex-shrink-0 text-rose-600" />
            <span>{error}</span>
          </div>
        )}

        {/* Search & Filter Toolbar */}
        <div className="bg-white border border-slate-200/90 rounded-2xl p-4 sm:p-5 shadow-sm space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-12 gap-3">
            {/* Search Input */}
            <div className="sm:col-span-6 relative">
              <div className="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                <Search className="w-4 h-4" />
              </div>
              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Tìm mã phiếu (INC-...), tiêu đề, mã TS, người báo cáo..."
                className="w-full pl-10 pr-4 py-2.5 bg-slate-50 border border-slate-200/90 focus:bg-white focus:border-rose-500 focus:ring-1 focus:ring-rose-500/20 rounded-xl text-xs text-slate-900 placeholder-slate-400 outline-none transition-all"
              />
            </div>

            {/* Status Filter */}
            <div className="sm:col-span-3">
              <select
                value={statusFilter}
                onChange={(e) => {
                  setStatusFilter(e.target.value);
                  setSkip(0);
                }}
                className="w-full py-2.5 px-3 bg-slate-50 border border-slate-200/90 focus:bg-white focus:border-rose-500 rounded-xl text-xs text-slate-700 outline-none transition-all"
              >
                <option value="">Tất cả Trạng thái</option>
                <option value="OPEN">Mới tạo (OPEN)</option>
                <option value="IN_REVIEW">Đang xem xét</option>
                <option value="IN_PROGRESS">Đang xử lý</option>
                <option value="WAITING_FOR_INFO">Chờ thông tin</option>
                <option value="RESOLVED">Đã khắc phục</option>
                <option value="CLOSED">Đã đóng</option>
                <option value="CANCELLED">Đã hủy</option>
              </select>
            </div>

            {/* Priority Filter */}
            <div className="sm:col-span-3">
              <select
                value={priorityFilter}
                onChange={(e) => {
                  setPriorityFilter(e.target.value);
                  setSkip(0);
                }}
                className="w-full py-2.5 px-3 bg-slate-50 border border-slate-200/90 focus:bg-white focus:border-rose-500 rounded-xl text-xs text-slate-700 outline-none transition-all"
              >
                <option value="">Tất cả Mức ưu tiên</option>
                <option value="CRITICAL">Khẩn cấp (CRITICAL)</option>
                <option value="HIGH">Cao (HIGH)</option>
                <option value="MEDIUM">Trung bình (MEDIUM)</option>
                <option value="LOW">Thấp (LOW)</option>
              </select>
            </div>
          </div>
        </div>

        {/* Table / List Area */}
        <div className="bg-white border border-slate-200/90 rounded-2xl shadow-sm overflow-hidden">
          {isLoading ? (
            <div className="p-12 flex flex-col items-center justify-center space-y-3">
              <Loader2 className="w-8 h-8 text-rose-600 animate-spin" />
              <span className="text-xs text-slate-500">Đang tải danh sách sự cố kỹ thuật...</span>
            </div>
          ) : incidents.length === 0 ? (
            <div className="p-12 text-center space-y-3">
              <AlertTriangle className="w-12 h-12 text-slate-300 mx-auto" />
              <div className="text-base font-semibold text-slate-700">Không có phiếu báo sự cố nào</div>
              <p className="text-xs text-slate-500 max-w-sm mx-auto">
                Chưa có sự cố được báo cáo hoặc không tìm thấy dữ liệu khớp với bộ lọc.
              </p>
            </div>
          ) : (
            <div className="w-full">
              <table className="w-full text-left text-xs text-slate-700">
                <thead className="bg-slate-50 text-slate-500 font-semibold uppercase tracking-wider border-b border-slate-200 text-[11px]">
                  <tr>
                    <th className="py-2.5 px-3">Mã Phiếu</th>
                    <th className="py-2.5 px-3">Tài Sản</th>
                    <th className="py-2.5 px-3">Tiêu Đề / Mô Tả</th>
                    <th className="py-2.5 px-3">Phân Loại / Ưu Tiên</th>
                    <th className="py-2.5 px-3">Trạng Thái</th>
                    <th className="py-2.5 px-3">Người Báo / IT</th>
                    <th className="py-2.5 px-3">Ngày Tạo</th>
                    <th className="py-2.5 px-3 text-right">Thao Tác</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {incidents.map((item) => (
                    <tr key={item.id} className="hover:bg-slate-50/80 transition-colors">
                      <td className="py-2.5 px-3 font-bold font-mono text-rose-600 whitespace-nowrap text-[11px]">
                        {item.ticket_code}
                      </td>
                      <td className="py-2.5 px-3 font-semibold text-slate-900">
                        <div className="font-mono text-indigo-600 text-[11px] truncate max-w-[120px]" title={item.asset?.asset_code}>
                          {item.asset?.asset_code || `TS #${item.asset_id}`}
                        </div>
                        <div className="text-slate-600 font-normal text-[11px] truncate max-w-[120px]" title={item.asset?.name}>{item.asset?.name}</div>
                      </td>
                      <td className="py-2.5 px-3 max-w-[200px]">
                        <div className="font-semibold text-slate-900 truncate" title={item.title}>{item.title}</div>
                        <div className="text-[11px] text-slate-500 truncate" title={item.description}>{item.description}</div>
                      </td>
                      <td className="py-2.5 px-3 space-y-0.5 whitespace-nowrap">
                        <div>{getPriorityBadge(item.priority)}</div>
                        <div className="text-[10px] text-slate-500 font-mono flex items-center space-x-1">
                          <span>{item.category}</span>
                          {item.suggested_queue && (
                            <span className="px-1 py-0.2 rounded bg-purple-50 text-purple-700 font-mono text-[9px] border border-purple-200">
                              {item.suggested_queue}
                            </span>
                          )}
                        </div>
                      </td>
                      <td className="py-2.5 px-3 whitespace-nowrap">
                        {getStatusBadge(item.status)}
                      </td>
                      <td className="py-2.5 px-3 whitespace-nowrap max-w-[140px]">
                        <div className="text-slate-900 font-medium truncate" title={item.reporter?.full_name || 'N/A'}>
                          {item.reporter?.full_name || 'N/A'}
                        </div>
                        <div className="text-slate-500 text-[10px] truncate" title={item.assigned_it?.full_name || 'Chưa gán'}>
                          IT: {item.assigned_it?.full_name || <span className="italic text-slate-400">Chưa gán</span>}
                        </div>
                      </td>
                      <td className="py-2.5 px-3 font-mono text-slate-500 text-[11px] whitespace-nowrap">
                        {formatDate(item.created_at)}
                      </td>
                      <td className="py-2.5 px-3 text-right whitespace-nowrap">
                        <div className="flex items-center justify-end space-x-1">
                          <button
                            onClick={() => openDetailModal(item)}
                            className="p-1.5 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 transition-colors"
                            title="Xem chi tiết"
                          >
                            <Eye className="w-3.5 h-3.5" />
                          </button>
                          {canManageIT && (
                            <>
                              <button
                                onClick={() => openRecommendationModal(item)}
                                className="p-1.5 rounded-lg bg-purple-50 hover:bg-purple-100 text-purple-700 border border-purple-200 transition-colors"
                                title="Đề xuất KTV (Smart Routing)"
                              >
                                <Sparkles className="w-3.5 h-3.5 text-purple-600" />
                              </button>
                              <button
                                onClick={() => openUpdateModal(item)}
                                className="p-1.5 rounded-lg bg-rose-50 hover:bg-rose-100 text-rose-700 border border-rose-200 transition-colors"
                                title="Xử lý / Cập nhật sự cố"
                              >
                                <Edit3 className="w-3.5 h-3.5" />
                              </button>
                              <Link
                                href="/maintenance"
                                className="p-1.5 rounded-lg bg-indigo-50 hover:bg-indigo-100 text-indigo-700 border border-indigo-200 transition-colors"
                                title="Lập phiếu bảo trì"
                              >
                                <Wrench className="w-3.5 h-3.5" />
                              </Link>
                            </>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Pagination Controls */}
          {total > limit && (
            <div className="px-4 py-3.5 bg-slate-50 border-t border-slate-200 flex items-center justify-between text-xs text-slate-600">
              <div>
                Hiển thị <span className="font-semibold text-slate-900">{skip + 1}</span> -{' '}
                <span className="font-semibold text-slate-900">
                  {Math.min(skip + limit, total)}
                </span>{' '}
                trên tổng số <span className="font-semibold text-slate-900">{total}</span> phiếu sự cố
              </div>
              <div className="flex items-center space-x-2">
                <button
                  disabled={skip === 0}
                  onClick={() => setSkip(Math.max(0, skip - limit))}
                  className="px-3 py-1.5 rounded-lg bg-white border border-slate-200 shadow-sm disabled:opacity-40 disabled:cursor-not-allowed hover:bg-slate-50 text-slate-700 font-medium"
                >
                  Trang trước
                </button>
                <button
                  disabled={skip + limit >= total}
                  onClick={() => setSkip(skip + limit)}
                  className="px-3 py-1.5 rounded-lg bg-white border border-slate-200 shadow-sm disabled:opacity-40 disabled:cursor-not-allowed hover:bg-slate-50 text-slate-700 font-medium"
                >
                  Trang sau
                </button>
              </div>
            </div>
          )}
        </div>
      </main>

      {/* CREATE INCIDENT MODAL */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/40 backdrop-blur-sm overflow-y-auto">
          <div className="w-full max-w-lg bg-white border border-slate-200/90 rounded-2xl shadow-2xl p-6 text-slate-800 my-8">
            <div className="flex items-center justify-between pb-4 border-b border-slate-100">
              <h3 className="text-lg font-bold text-slate-900 flex items-center space-x-2">
                <AlertTriangle className="w-5 h-5 text-rose-600" />
                <span>Báo cáo sự cố tài sản mới</span>
              </h3>
              <button
                onClick={() => setShowCreateModal(false)}
                className="text-slate-400 hover:text-slate-600"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {formError && (
              <div className="mt-4 p-3 rounded-xl bg-rose-50 border border-rose-200 text-rose-700 text-xs flex items-center space-x-2">
                <AlertCircle className="w-4 h-4 flex-shrink-0 text-rose-600" />
                <span>{formError}</span>
              </div>
            )}

            <form onSubmit={handleCreateSubmit} className="space-y-4 mt-4 text-xs">
              <div>
                <label className="block font-semibold text-slate-700 mb-1">
                  Chọn tài sản gặp sự cố <span className="text-rose-600">*</span>
                </label>
                <select
                  required
                  value={createFormData.asset_id}
                  onChange={(e) => setCreateFormData({ ...createFormData, asset_id: e.target.value })}
                  className="w-full p-2.5 bg-slate-50 border border-slate-200 rounded-xl focus:bg-white focus:border-rose-500 outline-none text-slate-900 font-mono"
                >
                  <option value="">-- Chọn tài sản --</option>
                  {assetsList.map((asset) => (
                    <option key={asset.id} value={asset.id}>
                      [{asset.asset_code}] {asset.name} ({asset.status})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">
                  Tiêu đề sự cố <span className="text-rose-600">*</span>
                </label>
                <input
                  type="text"
                  required
                  value={createFormData.title}
                  onChange={(e) => setCreateFormData({ ...createFormData, title: e.target.value })}
                  placeholder="VD: Màn hình không lên nguồn, quạt kêu to..."
                  className="w-full p-2.5 bg-slate-50 border border-slate-200 rounded-xl focus:bg-white focus:border-rose-500 outline-none text-slate-900"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Phân loại sự cố</label>
                  <select
                    value={createFormData.category}
                    onChange={(e) => setCreateFormData({ ...createFormData, category: e.target.value })}
                    className="w-full p-2.5 bg-slate-50 border border-slate-200 rounded-xl focus:bg-white focus:border-rose-500 outline-none text-slate-900"
                  >
                    <option value="HARDWARE">Phần cứng (HARDWARE)</option>
                    <option value="SOFTWARE">Phần mềm (SOFTWARE)</option>
                    <option value="NETWORK">Mạng internet (NETWORK)</option>
                    <option value="POWER">Nguồn điện (POWER)</option>
                    <option value="PHYSICAL_DAMAGE">Hỏng vật lý (PHYSICAL_DAMAGE)</option>
                    <option value="OTHER">Khác (OTHER)</option>
                  </select>
                </div>

                <div>
                  <label className="block font-semibold text-slate-700 mb-1">Mức độ ưu tiên</label>
                  <select
                    value={createFormData.priority}
                    onChange={(e) => setCreateFormData({ ...createFormData, priority: e.target.value })}
                    className="w-full p-2.5 bg-slate-50 border border-slate-200 rounded-xl focus:bg-white focus:border-rose-500 outline-none text-slate-900"
                  >
                    <option value="LOW">Thấp (LOW)</option>
                    <option value="MEDIUM">Trung bình (MEDIUM)</option>
                    <option value="HIGH">Cao (HIGH)</option>
                    <option value="CRITICAL">Khẩn cấp (CRITICAL)</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">
                  Mô tả chi tiết sự cố <span className="text-rose-600">*</span>
                </label>
                <textarea
                  rows={3}
                  required
                  value={createFormData.description}
                  onChange={(e) => setCreateFormData({ ...createFormData, description: e.target.value })}
                  placeholder="Mô tả hiện tượng, hoàn cảnh phát sinh lỗi..."
                  className="w-full p-2.5 bg-slate-50 border border-slate-200 rounded-xl focus:bg-white focus:border-rose-500 outline-none text-slate-900"
                />
              </div>

              {/* ATTACHMENT SELECTION SECTION IN CREATE MODAL */}
              <div className="pt-3 border-t border-slate-100 space-y-2.5">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                  <label className="font-semibold text-slate-700 flex items-center space-x-1.5">
                    <Paperclip className="w-4 h-4 text-amber-600" />
                    <span>Hình ảnh / tài liệu sự cố ({pendingFiles.length}/5)</span>
                  </label>

                  <div className="flex items-center space-x-2">
                    {/* Camera Input */}
                    <input
                      type="file"
                      ref={createCameraInputRef}
                      accept="image/*"
                      capture="environment"
                      className="hidden"
                      onChange={handleAddPendingFiles}
                    />
                    <button
                      type="button"
                      disabled={formSubmitting || pendingFiles.length >= 5}
                      onClick={() => createCameraInputRef.current?.click()}
                      className="px-2.5 py-1.5 rounded-lg bg-sky-50 hover:bg-sky-100 text-sky-700 border border-sky-200 text-[11px] font-semibold flex items-center space-x-1 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
                      title="Chụp ảnh trực tiếp từ thiết bị (Ưu tiên camera sau)"
                    >
                      <Camera className="w-3.5 h-3.5" />
                      <span>Chụp ảnh</span>
                    </button>

                    {/* File Picker Input */}
                    <input
                      type="file"
                      ref={createFilePickerInputRef}
                      accept=".jpg,.jpeg,.png,.webp,.pdf,.docx,.xlsx"
                      multiple
                      className="hidden"
                      onChange={handleAddPendingFiles}
                    />
                    <button
                      type="button"
                      disabled={formSubmitting || pendingFiles.length >= 5}
                      onClick={() => createFilePickerInputRef.current?.click()}
                      className="px-2.5 py-1.5 rounded-lg bg-amber-50 hover:bg-amber-100 text-amber-700 border border-amber-200 text-[11px] font-semibold flex items-center space-x-1 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
                      title="Chọn ảnh hoặc tài liệu từ máy tính / thiết bị"
                    >
                      <Upload className="w-3.5 h-3.5" />
                      <span>Chọn ảnh / tệp</span>
                    </button>
                  </div>
                </div>

                <p className="text-[11px] text-slate-500 italic">
                  * Giới hạn: tối đa 5 tệp, tối đa 10 MB/tệp (Hỗ trợ JPG, PNG, WEBP, PDF, DOCX, XLSX).
                </p>

                {/* Pending Files List */}
                {pendingFiles.length > 0 && (
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 max-h-40 overflow-y-auto pr-1">
                    {pendingFiles.map((file, idx) => {
                      const isImg = file.type.startsWith('image/');
                      const previewUrl = isImg ? URL.createObjectURL(file) : null;
                      const sizeKb = (file.size / 1024).toFixed(1);

                      return (
                        <div
                          key={idx}
                          className="p-2 bg-slate-50 border border-slate-200 rounded-xl flex items-center justify-between gap-2 text-xs"
                        >
                          <div className="flex items-center space-x-2 overflow-hidden">
                            {isImg && previewUrl ? (
                              <img
                                src={previewUrl}
                                alt={file.name}
                                className="w-9 h-9 object-cover rounded-lg border border-slate-200 shrink-0 bg-white"
                              />
                            ) : (
                              <div className="w-9 h-9 rounded-lg bg-amber-50 border border-amber-200 flex items-center justify-center text-amber-600 shrink-0">
                                <FileText className="w-4 h-4" />
                              </div>
                            )}
                            <div className="truncate">
                              <div className="font-semibold text-slate-800 truncate" title={file.name}>
                                {file.name}
                              </div>
                              <div className="text-[10px] text-slate-500 font-mono">
                                {sizeKb} KB
                              </div>
                            </div>
                          </div>

                          <button
                            type="button"
                            disabled={formSubmitting}
                            onClick={() => handleRemovePendingFile(idx)}
                            className="p-1 rounded-lg bg-rose-50 hover:bg-rose-100 text-rose-600 transition-colors shrink-0"
                            title="Xóa tệp khỏi danh sách"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>

              {uploadProgressMsg && (
                <div className="p-2.5 rounded-xl bg-purple-50 border border-purple-200 text-purple-800 text-xs flex items-center space-x-2 animate-pulse">
                  <Loader2 className="w-4 h-4 animate-spin flex-shrink-0 text-purple-600" />
                  <span>{uploadProgressMsg}</span>
                </div>
              )}

              <div className="flex items-center justify-end space-x-3 pt-4 border-t border-slate-100">
                <button
                  type="button"
                  disabled={formSubmitting}
                  onClick={() => setShowCreateModal(false)}
                  className="px-4 py-2.5 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold disabled:opacity-50"
                >
                  Hủy bỏ
                </button>
                <button
                  type="submit"
                  disabled={formSubmitting}
                  className="flex items-center space-x-2 px-5 py-2.5 rounded-xl bg-rose-600 hover:bg-rose-700 text-white font-semibold shadow-md shadow-rose-600/20 disabled:opacity-60"
                >
                  {formSubmitting ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      <span>Đang xử lý...</span>
                    </>
                  ) : (
                    <span>Gửi báo cáo sự cố</span>
                  )}
                </button>
              </div>

            </form>
          </div>
        </div>
      )}

      {/* UPDATE INCIDENT MODAL (ADMIN / IT MANAGER ONLY) */}
      {showUpdateModal && selectedIncident && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/40 backdrop-blur-sm overflow-y-auto">
          <div className="w-full max-w-lg bg-white border border-slate-200/90 rounded-2xl shadow-2xl p-6 text-slate-800 my-8">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <h3 className="text-lg font-bold text-slate-900 flex items-center space-x-2">
                <Wrench className="w-5 h-5 text-rose-600" />
                <span>Xử lý phiếu: {selectedIncident.ticket_code}</span>
              </h3>
              <button
                onClick={() => setShowUpdateModal(false)}
                className="text-slate-400 hover:text-slate-600"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {formError && (
              <div className="mt-4 p-3 rounded-xl bg-rose-50 border border-rose-200 text-rose-700 text-xs flex items-center space-x-2">
                <AlertCircle className="w-4 h-4 flex-shrink-0 text-rose-600" />
                <span>{formError}</span>
              </div>
            )}

            <form onSubmit={handleUpdateSubmit} className="space-y-4 mt-4 text-xs">
              <div className="p-3 bg-slate-50 border border-slate-200 rounded-xl space-y-1">
                <div>
                  Tài sản:{' '}
                  <span className="font-bold text-indigo-600 font-mono">
                    {selectedIncident.asset?.asset_code}
                  </span>{' '}
                  - {selectedIncident.asset?.name}
                </div>
                <div>Tiêu đề: <span className="font-semibold text-slate-900">{selectedIncident.title}</span></div>
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">Cập nhật trạng thái phiếu</label>
                <select
                  value={updateFormData.status}
                  disabled={selectedIncident.status === 'CLOSED' || selectedIncident.status === 'CANCELLED'}
                  onChange={(e) => setUpdateFormData({ ...updateFormData, status: e.target.value })}
                  className="w-full p-2.5 bg-slate-50 border border-slate-200 rounded-xl focus:bg-white focus:border-rose-500 outline-none text-slate-900 disabled:opacity-60 disabled:cursor-not-allowed"
                >
                  {(VALID_STATUS_TRANSITIONS[selectedIncident.status] || [
                    { value: selectedIncident.status, label: selectedIncident.status }
                  ]).map((opt) => (
                    <option key={opt.value} value={opt.value}>
                      {opt.label}
                    </option>
                  ))}
                </select>
                {(selectedIncident.status === 'CLOSED' || selectedIncident.status === 'CANCELLED') && (
                  <p className="text-[11px] text-slate-500 mt-1 italic">
                    Phiếu đã ở trạng thái kết thúc ({selectedIncident.status}), không thể chuyển trạng thái.
                  </p>
                )}
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">Phân công cán bộ IT phụ trách</label>
                <select
                  value={updateFormData.assigned_it_id}
                  onChange={(e) => setUpdateFormData({ ...updateFormData, assigned_it_id: e.target.value })}
                  className="w-full p-2.5 bg-slate-50 border border-slate-200 rounded-xl focus:bg-white focus:border-rose-500 outline-none text-slate-900"
                >
                  <option value="">-- Chưa gán cán bộ --</option>
                  {itUsersList.map((u) => (
                    <option key={u.id} value={u.id}>
                      {u.full_name} ({u.email}) - {u.role}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">Chi phí sửa chữa (VND)</label>
                <input
                  type="number"
                  min="0"
                  step="1000"
                  value={updateFormData.repair_cost}
                  onChange={(e) => setUpdateFormData({ ...updateFormData, repair_cost: e.target.value })}
                  className="w-full p-2.5 bg-slate-50 border border-slate-200 rounded-xl focus:bg-white focus:border-rose-500 outline-none text-slate-900 font-mono"
                />
              </div>

              <div>
                <label className="block font-semibold text-slate-700 mb-1">Ghi chú khắc phục / Phương án xử lý</label>
                <textarea
                  rows={3}
                  value={updateFormData.resolution_notes}
                  onChange={(e) => setUpdateFormData({ ...updateFormData, resolution_notes: e.target.value })}
                  placeholder="Ghi rõ chi tiết phương án đã thay thế, sửa chữa..."
                  className="w-full p-2.5 bg-slate-50 border border-slate-200 rounded-xl focus:bg-white focus:border-rose-500 outline-none text-slate-900"
                />
              </div>

              <div className="flex items-center justify-end space-x-3 pt-3 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setShowUpdateModal(false)}
                  className="px-4 py-2.5 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold"
                >
                  Hủy
                </button>
                <button
                  type="submit"
                  disabled={formSubmitting}
                  className="flex items-center space-x-2 px-5 py-2.5 rounded-xl bg-rose-600 hover:bg-rose-700 text-white font-semibold shadow-md shadow-rose-600/20 disabled:opacity-60"
                >
                  {formSubmitting ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      <span>Đang lưu...</span>
                    </>
                  ) : (
                    <span>Lưu cập nhật</span>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* DETAIL MODAL */}
      {showDetailModal && selectedIncident && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/40 backdrop-blur-sm overflow-y-auto">
          <div className="w-full max-w-2xl bg-white border border-slate-200/90 rounded-2xl shadow-2xl p-6 text-slate-800 space-y-4 my-8">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <div className="flex items-center space-x-2">
                <AlertTriangle className="w-5 h-5 text-rose-600" />
                <span className="font-mono text-rose-600 font-bold text-base">
                  {selectedIncident.ticket_code}
                </span>
              </div>
              <button
                onClick={() => setShowDetailModal(false)}
                className="text-slate-400 hover:text-slate-600"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div>
              <h3 className="text-lg font-bold text-slate-900 leading-snug">{selectedIncident.title}</h3>
              <div className="mt-2 flex items-center space-x-2">
                {getStatusBadge(selectedIncident.status)}
                {getPriorityBadge(selectedIncident.priority)}
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3 text-xs bg-slate-50 p-4 rounded-xl border border-slate-200/80">
              <div>
                <div className="text-slate-500 uppercase font-medium text-[10px]">Tài sản gặp sự cố</div>
                <div className="font-semibold text-slate-900 mt-0.5">
                  [{selectedIncident.asset?.asset_code}] {selectedIncident.asset?.name}
                </div>
              </div>
              <div>
                <div className="text-slate-500 uppercase font-medium text-[10px]">Người báo cáo</div>
                <div className="font-semibold text-slate-800 mt-0.5">
                  {selectedIncident.reporter?.full_name} ({selectedIncident.reporter?.email})
                </div>
              </div>
              <div>
                <div className="text-slate-500 uppercase font-medium text-[10px]">Cán bộ IT phụ trách</div>
                <div className="font-semibold text-slate-800 mt-0.5">
                  {selectedIncident.assigned_it?.full_name || 'Chưa phân công'}
                </div>
              </div>
              <div>
                <div className="text-slate-500 uppercase font-medium text-[10px]">Chi phí sửa chữa</div>
                <div className="font-mono font-semibold text-emerald-600 mt-0.5">
                  {selectedIncident.repair_cost ? `${selectedIncident.repair_cost.toLocaleString('vi-VN')} VNĐ` : '0 VNĐ'}
                </div>
              </div>
            </div>

            <div className="text-xs space-y-1">
              <div className="text-slate-500 uppercase font-medium text-[10px]">Mô tả sự cố</div>
              <div className="p-3 bg-slate-50 border border-slate-200/80 rounded-xl text-slate-700">
                {selectedIncident.description}
              </div>
            </div>

            {selectedIncident.resolution_notes && (
              <div className="text-xs space-y-1">
                <div className="text-slate-500 uppercase font-medium text-[10px]">Ghi chú khắc phục / Xử lý</div>
                <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-xl text-emerald-800">
                  {selectedIncident.resolution_notes}
                </div>
              </div>
            )}

            {/* SEAWEEDFS ATTACHMENTS SECTION */}
            <div className="pt-3 border-t border-slate-100 space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2 text-amber-700 font-bold text-xs uppercase tracking-wider">
                  <Paperclip className="w-4 h-4 text-amber-600" />
                  <span>Tập tin đính kèm (SeaweedFS) ({attachmentsList.length}/5)</span>
                </div>
                <div>
                  <input
                    type="file"
                    ref={fileInputRef}
                    onChange={handleFileUpload}
                    className="hidden"
                    accept=".jpg,.jpeg,.png,.webp,.pdf,.docx,.xlsx"
                  />
                  <button
                    type="button"
                    disabled={uploadingAttachment || attachmentsList.length >= 5}
                    onClick={() => fileInputRef.current?.click()}
                    className="px-3 py-1.5 rounded-lg bg-amber-50 hover:bg-amber-100 text-amber-700 border border-amber-200 text-xs font-semibold flex items-center space-x-1.5 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
                  >
                    {uploadingAttachment ? (
                      <>
                        <Loader2 className="w-3.5 h-3.5 animate-spin text-amber-600" />
                        <span>Đang tải lên...</span>
                      </>
                    ) : (
                      <>
                        <Upload className="w-3.5 h-3.5" />
                        <span>+ Tải lên đính kèm</span>
                      </>
                    )}
                  </button>
                </div>
              </div>

              {attachmentsList.length === 0 ? (
                <div className="p-3 bg-slate-50 border border-slate-200 rounded-xl text-xs text-slate-500 text-center">
                  Chưa có tập tin đính kèm (Hỗ trợ định dạng: JPG, PNG, WEBP, PDF, DOCX, XLSX - Tối đa 10MB).
                </div>
              ) : (
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 max-h-48 overflow-y-auto pr-1">
                  {attachmentsList.map((att) => {
                    const isImg = att.mime_type.startsWith('image/');
                    const imgBlobUrl = previewBlobs[att.id];
                    const sizeKb = (att.file_size / 1024).toFixed(1);

                    return (
                      <div
                        key={att.id}
                        className="p-2.5 bg-slate-50 border border-slate-200 rounded-xl flex items-center justify-between gap-2 text-xs hover:border-slate-300 transition-all"
                      >
                        <div className="flex items-center space-x-2.5 overflow-hidden">
                          {isImg && imgBlobUrl ? (
                            <img
                              src={imgBlobUrl}
                              alt={att.file_name}
                              className="w-10 h-10 object-cover rounded-lg border border-slate-200 shrink-0 bg-white"
                            />
                          ) : isImg ? (
                            <div className="w-10 h-10 rounded-lg bg-amber-50 border border-amber-200 flex items-center justify-center text-amber-600 shrink-0">
                              <ImageIcon className="w-5 h-5 animate-pulse" />
                            </div>
                          ) : (
                            <div className="w-10 h-10 rounded-lg bg-amber-50 border border-amber-200 flex items-center justify-center text-amber-600 shrink-0">
                              <FileText className="w-5 h-5" />
                            </div>
                          )}
                          <div className="truncate">
                            <div className="font-semibold text-slate-800 truncate" title={att.file_name}>
                              {att.file_name}
                            </div>
                            <div className="text-[10px] text-slate-500 font-mono">
                              {sizeKb} KB • {att.mime_type.split('/')[1] || 'file'}
                            </div>
                          </div>
                        </div>

                        <div className="flex items-center space-x-1 shrink-0">
                          <button
                            type="button"
                            onClick={() => handleDownloadAttachment(att)}
                            className="p-1.5 rounded-lg bg-white border border-slate-200 hover:bg-slate-100 text-slate-700 transition-colors shadow-sm"
                            title="Tải về / Xem tập tin"
                          >
                            <Download className="w-3.5 h-3.5" />
                          </button>
                          {(att.uploaded_by_id === user?.id || user?.role === 'ADMIN' || user?.role === 'IT_ASSET_MANAGER') && (
                            <button
                              type="button"
                              onClick={() => handleDeleteAttachment(att.id)}
                              className="p-1.5 rounded-lg bg-rose-50 hover:bg-rose-100 text-rose-600 transition-colors"
                              title="Xóa tập tin đính kèm"
                            >
                              <Trash2 className="w-3.5 h-3.5" />
                            </button>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>

            {/* KNOWLEDGE BASE / SIMILAR INCIDENTS SECTION */}
            <div className="pt-3 border-t border-slate-100 space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2 text-indigo-700 font-bold text-xs uppercase tracking-wider">
                  <BookOpen className="w-4 h-4 text-indigo-600" />
                  <span>🔎 Sự cố tương tự trong Knowledge Base</span>
                </div>
                {similarIncidents && (
                  <span className="text-[11px] text-slate-500">
                    Tìm thấy: <strong className="text-indigo-600">{similarIncidents.total_found}</strong> sự cố
                  </span>
                )}
              </div>

              {loadingSimilar ? (
                <div className="p-4 bg-slate-50 border border-slate-200 rounded-xl flex items-center justify-center space-x-2 text-xs text-slate-500">
                  <Loader2 className="w-4 h-4 animate-spin text-indigo-600" />
                  <span>Đang truy vấn Knowledge Base...</span>
                </div>
              ) : !similarIncidents || similarIncidents.items.length === 0 ? (
                <div className="p-3 bg-slate-50 border border-slate-200 rounded-xl text-xs text-slate-500 text-center">
                  Chưa tìm thấy sự cố tương tự phù hợp trong Knowledge Base (Ngưỡng khớp score ≥ 30).
                </div>
              ) : (
                <div className="space-y-2.5 max-h-60 overflow-y-auto pr-1">
                  {similarIncidents.items.map((item) => (
                    <div
                      key={item.incident_id}
                      className="p-3 bg-slate-50 border border-slate-200 rounded-xl space-y-2 text-xs"
                    >
                      <div className="flex items-start justify-between gap-2">
                        <div>
                          <div className="flex items-center space-x-2">
                            <span className="font-mono text-indigo-600 font-bold">{item.ticket_code}</span>
                            <span className="font-semibold text-slate-900">{item.title}</span>
                          </div>
                          <div className="text-[10px] text-slate-500 mt-0.5">
                            Tài sản: {item.asset_name} ({item.asset_code}) • {item.category}
                          </div>
                        </div>
                        <div className="flex flex-col items-end shrink-0">
                          <span className="px-2 py-0.5 rounded-full bg-indigo-50 text-indigo-700 border border-indigo-200 text-[10px] font-bold">
                            Khớp {item.similarity_score}%
                          </span>
                          {item.resolved_at && (
                            <span className="text-[10px] text-slate-500 mt-0.5">
                              {formatDate(item.resolved_at)}
                            </span>
                          )}
                        </div>
                      </div>

                      {/* Similarity Reasons */}
                      {item.similarity_reasons && item.similarity_reasons.length > 0 && (
                        <div className="flex flex-wrap gap-1">
                          {item.similarity_reasons.map((reason, rIdx) => (
                            <span
                              key={rIdx}
                              className="px-1.5 py-0.5 rounded bg-white text-[10px] text-slate-600 border border-slate-200"
                            >
                              ✓ {reason}
                            </span>
                          ))}
                        </div>
                      )}

                      {/* Resolution Notes */}
                      {item.resolution_notes && (
                        <div className="p-2 bg-emerald-50 border border-emerald-200 rounded-lg text-emerald-800 text-[11px]">
                          <strong className="text-emerald-700 font-semibold">Cách đã xử lý: </strong>
                          {item.resolution_notes}
                        </div>
                      )}

                      {/* Linked Maintenance Info if present */}
                      {item.linked_maintenance && (
                        <div className="flex flex-wrap items-center justify-between text-[10px] text-slate-500 pt-1 border-t border-slate-200">
                          <div>
                            Bảo trì: <span className="text-slate-800 font-mono font-medium">{item.linked_maintenance.maintenance_code}</span> ({item.linked_maintenance.status})
                          </div>
                          {item.linked_maintenance.duration_hours !== null && (
                            <div>
                              Thời gian xử lý: <span className="text-amber-700 font-medium">{item.linked_maintenance.duration_hours} giờ</span>
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div className="flex items-center justify-between text-[11px] text-slate-500 pt-3 border-t border-slate-100">
              <div>Ngày tạo: {formatDate(selectedIncident.created_at)}</div>
              <button
                onClick={() => setShowDetailModal(false)}
                className="px-4 py-2 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold"
              >
                Đóng
              </button>
            </div>
          </div>
        </div>
      )}

      {/* RECOMMENDATION MODAL (SMART ROUTING & TECHNICIAN RECOMMENDATION) */}
      {showRecommendationModal && selectedIncident && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/40 backdrop-blur-sm overflow-y-auto">
          <div className="w-full max-w-2xl bg-white border border-purple-200 rounded-2xl shadow-2xl p-6 text-slate-800 my-8 space-y-5">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <div className="flex items-center space-x-2">
                <div className="w-9 h-9 rounded-xl bg-purple-50 border border-purple-200 flex items-center justify-center text-purple-600">
                  <Sparkles className="w-5 h-5" />
                </div>
                <div>
                  <h3 className="text-lg font-bold text-slate-900 tracking-tight">
                    Smart Routing & Đề xuất Kỹ thuật viên
                  </h3>
                  <p className="text-xs text-slate-500">
                    Phiếu sự cố: <span className="font-mono text-purple-700 font-semibold">{selectedIncident.ticket_code}</span> - {selectedIncident.title}
                  </p>
                </div>
              </div>
              <button
                onClick={() => setShowRecommendationModal(false)}
                className="text-slate-400 hover:text-slate-600"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* AI Classification & Queue Card */}
            <div className="bg-purple-50/50 border border-purple-100 rounded-xl p-4 grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
              <div>
                <div className="text-[10px] uppercase font-semibold text-slate-500">Danh mục Sự cố</div>
                <div className="font-bold text-slate-900 mt-1 flex items-center space-x-1.5">
                  <Cpu className="w-4 h-4 text-indigo-600" />
                  <span>{selectedIncident.category}</span>
                </div>
              </div>
              <div>
                <div className="text-[10px] uppercase font-semibold text-slate-500">Queue Xử lý Gợi ý</div>
                <div className="font-mono font-bold text-purple-700 mt-1 flex items-center space-x-1.5">
                  <Layers className="w-4 h-4 text-purple-600" />
                  <span>{recommendationsData?.suggested_queue || selectedIncident.suggested_queue || 'GENERAL_SUPPORT'}</span>
                </div>
              </div>
              <div>
                <div className="text-[10px] uppercase font-semibold text-slate-500">Chế độ phân công</div>
                <div className="font-semibold text-amber-700 mt-1 flex items-center space-x-1.5">
                  <UserCheck className="w-4 h-4 text-amber-600" />
                  <span>Xác nhận bởi Quản trị</span>
                </div>
              </div>
            </div>

            {/* Candidates List */}
            <div className="space-y-3">
              <h4 className="text-xs font-bold uppercase tracking-wider text-slate-700 flex items-center justify-between">
                <span>Bảng xếp hạng Kỹ thuật viên phù hợp (100-pt Scoring)</span>
                <span className="text-[11px] text-slate-400 font-normal">Skill (40) + Workload (40) + SLA (20)</span>
              </h4>

              {loadingRecommendations ? (
                <div className="p-8 flex flex-col items-center justify-center space-y-2">
                  <Loader2 className="w-7 h-7 text-purple-600 animate-spin" />
                  <span className="text-xs text-slate-500">Đang phân tích dữ liệu kỹ năng & workload...</span>
                </div>
              ) : !recommendationsData || recommendationsData.recommendations.length === 0 ? (
                <div className="p-6 text-center text-xs text-slate-500 border border-slate-200 rounded-xl">
                  Không tìm thấy Kỹ thuật viên phù hợp trong hệ thống.
                </div>
              ) : (
                <div className="space-y-3 max-h-80 overflow-y-auto pr-1">
                  {recommendationsData.recommendations.map((tech, idx) => (
                    <div
                      key={tech.user_id}
                      className={`p-4 rounded-xl border transition-all ${
                        idx === 0
                          ? 'bg-purple-50/70 border-purple-200 shadow-sm'
                          : 'bg-slate-50 border-slate-200 hover:border-slate-300'
                      }`}
                    >
                      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                        <div className="space-y-1">
                          <div className="flex items-center space-x-2">
                            {idx === 0 && (
                              <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-100 text-amber-800 border border-amber-200">
                                ★ TOP 1 ĐỀ XUẤT
                              </span>
                            )}
                            <span className="font-bold text-slate-900 text-sm">{tech.full_name}</span>
                            <span className="text-xs text-slate-500">({tech.email})</span>
                          </div>
                          <div className="flex flex-wrap gap-2 pt-1 text-[11px]">
                            {tech.reasons.map((r, rIdx) => (
                              <span key={rIdx} className="px-2 py-0.5 rounded bg-white text-slate-700 border border-slate-200">
                                {r}
                              </span>
                            ))}
                          </div>
                        </div>

                        <div className="flex items-center space-x-3 flex-shrink-0">
                          <div className="text-right">
                            <div className="text-xs text-slate-500">Đồ thị Phù hợp</div>
                            <div className="text-lg font-extrabold font-mono text-purple-700">
                              {tech.total_score}<span className="text-xs text-slate-400">/100</span>
                            </div>
                          </div>
                          <button
                            disabled={assigningTechId === tech.user_id}
                            onClick={() => handleAssignTechnician(selectedIncident.id, tech.user_id)}
                            className="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white font-semibold text-xs rounded-xl shadow-md transition-all flex items-center space-x-1.5 disabled:opacity-50"
                          >
                            {assigningTechId === tech.user_id ? (
                              <Loader2 className="w-4 h-4 animate-spin" />
                            ) : (
                              <>
                                <CheckCircle2 className="w-4 h-4" />
                                <span>Phân công</span>
                              </>
                            )}
                          </button>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div className="flex items-center justify-between text-[11px] text-slate-500 pt-3 border-t border-slate-100">
              <div className="italic text-slate-400">
                AI đóng vai trò hỗ trợ điều phối. Việc giao việc hoàn toàn nằm trong quyết định của bạn.
              </div>
              <button
                onClick={() => setShowRecommendationModal(false)}
                className="px-4 py-2 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold"
              >
                Đóng
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default function IncidentsPage() {
  return (
    <ProtectedRoute>
      <IncidentsContent />
    </ProtectedRoute>
  );
}

