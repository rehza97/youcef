import React, { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Checkbox } from '@/components/ui/checkbox';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Separator } from '@/components/ui/separator';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import {
  Plus,
  Edit,
  Trash2,
  RefreshCw,
  Search,
  Info,
  Network,
  BarChart3,
  Check,
  X,
} from 'lucide-react';
import { toast } from 'sonner';
import api from '@/services/api';

// Module constants
const MODULES = [
  { value: 'parc_corporate_ngbss', label: 'Parc Corporate NGBSS', color: '#1976d2' },
  { value: 'chiffre_affaires', label: 'Chiffre d\'Affaires', color: '#2e7d32' },
  { value: 'encaissement_ar_dot', label: 'Encaissement AR DOT', color: '#ed6c02' },
  { value: 'creance_periodique_dot', label: 'Créance Périodique DOT', color: '#9c27b0' },
  { value: null, label: 'Global (All Modules)', color: '#757575' },
];

interface DOT {
  id: number;
  name: string;
  module: string | null;
  description: string | null;
  created_at: string | null;
  updated_at: string | null;
}

interface DOTUsageStats {
  dot_id: number;
  dot_name: string;
  module: string | null;
  users_count: number;
  parks_count: number;
  revenue_records: number;
  encaissement_records: number;
  creance_records: number;
  can_delete: boolean;
  deletion_blockers: string[];
}

interface DOTModuleSummary {
  module: string | null;
  count: number;
  dots: DOT[];
}

const DOTManagementPage: React.FC = () => {
  // State
  const [dots, setDots] = useState<DOT[]>([]);
  const [filteredDots, setFilteredDots] = useState<DOT[]>([]);
  const [moduleSummary, setModuleSummary] = useState<DOTModuleSummary[]>([]);
  const [selectedModule, setSelectedModule] = useState<string | null>('ALL');
  const [searchQuery, setSearchQuery] = useState('');
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(25);
  const [totalCount, setTotalCount] = useState(0);
  const [loading, setLoading] = useState(false);
  const [selectedDots, setSelectedDots] = useState<number[]>([]);
  const [currentTab, setCurrentTab] = useState('all');

  // Dialog states
  const [openCreateDialog, setOpenCreateDialog] = useState(false);
  const [openEditDialog, setOpenEditDialog] = useState(false);
  const [openDeleteDialog, setOpenDeleteDialog] = useState(false);
  const [openUsageDialog, setOpenUsageDialog] = useState(false);
  const [openBulkUpdateDialog, setOpenBulkUpdateDialog] = useState(false);

  // Form states
  const [formData, setFormData] = useState({
    name: '',
    module: null as string | null,
    description: '',
  });
  const [editingDot, setEditingDot] = useState<DOT | null>(null);
  const [dotUsageStats, setDotUsageStats] = useState<DOTUsageStats | null>(null);
  const [bulkUpdateModule, setBulkUpdateModule] = useState<string | null>(null);

  // Load DOTs
  useEffect(() => {
    fetchDots();
    fetchModuleSummary();
  }, [page, rowsPerPage, selectedModule, searchQuery]);

  // Filter DOTs
  useEffect(() => {
    if (selectedModule === 'ALL') {
      setFilteredDots(dots);
    } else {
      setFilteredDots(dots.filter(dot =>
        selectedModule === 'NULL'
          ? dot.module === null
          : dot.module === selectedModule
      ));
    }
  }, [dots, selectedModule]);

  const fetchDots = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams({
        page: (page + 1).toString(),
        page_size: rowsPerPage.toString(),
      });

      if (searchQuery) {
        params.append('search', searchQuery);
      }

      if (selectedModule && selectedModule !== 'ALL' && selectedModule !== 'NULL') {
        params.append('module', selectedModule);
      }

      const response = await api.get(`/api/dots?${params}`);
      setDots(response.data.items);
      setTotalCount(response.data.total);
    } catch (error: any) {
      toast.error('Failed to fetch DOTs: ' + (error.response?.data?.detail || error.message));
    } finally {
      setLoading(false);
    }
  };

  const fetchModuleSummary = async () => {
    try {
      const response = await api.get('/api/dots/modules/summary');
      setModuleSummary(response.data);
    } catch (error: any) {
      console.error('Failed to fetch module summary:', error);
    }
  };

  const fetchDotUsage = async (dotId: number) => {
    try {
      const response = await api.get(`/api/dots/${dotId}/usage`);
      setDotUsageStats(response.data);
      setOpenUsageDialog(true);
    } catch (error: any) {
      toast.error('Failed to fetch DOT usage stats: ' + (error.response?.data?.detail || error.message));
    }
  };

  const handleCreateDot = async () => {
    try {
      await api.post('/api/dots/', formData);
      toast.success('DOT created successfully!');
      setOpenCreateDialog(false);
      resetForm();
      fetchDots();
      fetchModuleSummary();
    } catch (error: any) {
      toast.error('Failed to create DOT: ' + (error.response?.data?.detail || error.message));
    }
  };

  const handleUpdateDot = async () => {
    if (!editingDot) return;

    try {
      await api.put(`/api/dots/${editingDot.id}`, formData);
      toast.success('DOT updated successfully!');
      setOpenEditDialog(false);
      setEditingDot(null);
      resetForm();
      fetchDots();
      fetchModuleSummary();
    } catch (error: any) {
      toast.error('Failed to update DOT: ' + (error.response?.data?.detail || error.message));
    }
  };

  const handleDeleteDot = async (dotId: number) => {
    try {
      await api.delete(`/api/dots/${dotId}`);
      toast.success('DOT deleted successfully!');
      setOpenDeleteDialog(false);
      setEditingDot(null);
      fetchDots();
      fetchModuleSummary();
    } catch (error: any) {
      toast.error('Failed to delete DOT: ' + (error.response?.data?.detail || error.message));
    }
  };

  const handleBulkUpdate = async () => {
    if (selectedDots.length === 0) {
      toast.warning('Please select DOTs to update');
      return;
    }

    try {
      await api.post('/api/dots/bulk-update', {
        dot_ids: selectedDots,
        module: bulkUpdateModule,
      });
      toast.success(`Updated ${selectedDots.length} DOT(s) successfully!`);
      setOpenBulkUpdateDialog(false);
      setSelectedDots([]);
      setBulkUpdateModule(null);
      fetchDots();
      fetchModuleSummary();
    } catch (error: any) {
      toast.error('Failed to bulk update: ' + (error.response?.data?.detail || error.message));
    }
  };

  const resetForm = () => {
    setFormData({
      name: '',
      module: null,
      description: '',
    });
  };

  const openEditDialogWithDot = (dot: DOT) => {
    setEditingDot(dot);
    setFormData({
      name: dot.name,
      module: dot.module,
      description: dot.description || '',
    });
    setOpenEditDialog(true);
  };

  const openDeleteDialogWithDot = async (dot: DOT) => {
    await fetchDotUsage(dot.id);
    setEditingDot(dot);
    setOpenDeleteDialog(true);
  };

  const toggleDotSelection = (dotId: number) => {
    setSelectedDots(prev =>
      prev.includes(dotId)
        ? prev.filter(id => id !== dotId)
        : [...prev, dotId]
    );
  };

  const selectAllDots = () => {
    if (selectedDots.length === filteredDots.length) {
      setSelectedDots([]);
    } else {
      setSelectedDots(filteredDots.map(dot => dot.id));
    }
  };

  const getModuleColor = (module: string | null) => {
    const moduleConfig = MODULES.find(m => m.value === module);
    return moduleConfig?.color || '#757575';
  };

  const getModuleLabel = (module: string | null) => {
    const moduleConfig = MODULES.find(m => m.value === module);
    return moduleConfig?.label || 'Global';
  };

  return (
    <div className="container mx-auto py-6 space-y-6">
      {/* Header */}
      <div className="space-y-2">
        <h1 className="text-3xl font-bold">DOT Management</h1>
        <p className="text-muted-foreground">
          Manage Digital Operations Telecommunication (DOT) regions and their module assignments
        </p>
      </div>

      {/* Tabs */}
      <Tabs value={currentTab} onValueChange={setCurrentTab} className="space-y-4">
        <TabsList>
          <TabsTrigger value="all" className="flex items-center gap-2">
            <Network className="h-4 w-4" />
            All DOTs
          </TabsTrigger>
          <TabsTrigger value="summary" className="flex items-center gap-2">
            <BarChart3 className="h-4 w-4" />
            Module Summary
          </TabsTrigger>
        </TabsList>

        {/* Tab 0: All DOTs */}
        <TabsContent value="all" className="space-y-4">
          {/* Summary Cards */}
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
            {moduleSummary.map((summary) => (
              <Card
                key={summary.module || 'null'}
                className={`cursor-pointer transition-all ${
                  selectedModule === (summary.module || 'NULL')
                    ? 'ring-2'
                    : ''
                }`}
                style={{
                  borderColor: selectedModule === (summary.module || 'NULL')
                    ? getModuleColor(summary.module)
                    : undefined,
                }}
                onClick={() => setSelectedModule(summary.module || 'NULL')}
              >
                <CardContent className="pt-6">
                  <p className="text-xs text-muted-foreground mb-1">
                    {getModuleLabel(summary.module)}
                  </p>
                  <h3 className="text-2xl font-bold mb-1" style={{ color: getModuleColor(summary.module) }}>
                    {summary.count}
                  </h3>
                  <p className="text-xs text-muted-foreground">
                    DOT{summary.count !== 1 ? 's' : ''}
                  </p>
                </CardContent>
              </Card>
            ))}
            <Card
              className={`cursor-pointer transition-all ${
                selectedModule === 'ALL' ? 'ring-2 ring-primary' : ''
              }`}
              onClick={() => setSelectedModule('ALL')}
            >
              <CardContent className="pt-6">
                <p className="text-xs text-muted-foreground mb-1">
                  All Modules
                </p>
                <h3 className="text-2xl font-bold mb-1 text-primary">
                  {totalCount}
                </h3>
                <p className="text-xs text-muted-foreground">
                  Total DOTs
                </p>
              </CardContent>
            </Card>
          </div>

          {/* Toolbar */}
          <Card>
            <CardContent className="pt-6">
              <div className="flex flex-col md:flex-row gap-4 items-center">
                <div className="flex-1 w-full md:w-auto">
                  <div className="relative">
                    <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                    <Input
                      placeholder="Search DOTs..."
                      value={searchQuery}
                      onChange={(e) => setSearchQuery(e.target.value)}
                      className="pl-9"
                    />
                  </div>
                </div>
                <div className="w-full md:w-[200px]">
                  <Select
                    value={selectedModule || 'ALL'}
                    onValueChange={(value) => setSelectedModule(value)}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Module Filter" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="ALL">All Modules</SelectItem>
                      <SelectItem value="NULL">Global (No Module)</SelectItem>
                      <Separator className="my-1" />
                      {MODULES.filter(m => m.value !== null).map((module) => (
                        <SelectItem key={module.value} value={module.value || ''}>
                          {module.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="flex gap-2">
                  {selectedDots.length > 0 && (
                    <Button
                      variant="outline"
                      onClick={() => setOpenBulkUpdateDialog(true)}
                    >
                      <Edit className="h-4 w-4 mr-2" />
                      Bulk Update ({selectedDots.length})
                    </Button>
                  )}
                  <Button
                    variant="outline"
                    onClick={fetchDots}
                  >
                    <RefreshCw className="h-4 w-4 mr-2" />
                    Refresh
                  </Button>
                  <Button
                    onClick={() => setOpenCreateDialog(true)}
                  >
                    <Plus className="h-4 w-4 mr-2" />
                    Create DOT
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Table */}
          <Card>
            <CardContent className="p-0">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-12">
                      <Checkbox
                        checked={selectedDots.length === filteredDots.length && filteredDots.length > 0}
                        onCheckedChange={selectAllDots}
                      />
                    </TableHead>
                    <TableHead>ID</TableHead>
                    <TableHead>Name</TableHead>
                    <TableHead>Module</TableHead>
                    <TableHead>Description</TableHead>
                    <TableHead>Created</TableHead>
                    <TableHead>Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {loading ? (
                    <TableRow>
                      <TableCell colSpan={7} className="text-center py-8">
                        <div className="flex items-center justify-center">
                          <RefreshCw className="h-4 w-4 animate-spin mr-2" />
                          Loading...
                        </div>
                      </TableCell>
                    </TableRow>
                  ) : filteredDots.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={7} className="text-center py-8 text-muted-foreground">
                        No DOTs found
                      </TableCell>
                    </TableRow>
                  ) : (
                    filteredDots.map((dot) => (
                      <TableRow key={dot.id}>
                        <TableCell>
                          <Checkbox
                            checked={selectedDots.includes(dot.id)}
                            onCheckedChange={() => toggleDotSelection(dot.id)}
                          />
                        </TableCell>
                        <TableCell>{dot.id}</TableCell>
                        <TableCell className="font-medium">
                          {dot.name}
                        </TableCell>
                        <TableCell>
                          <Badge
                            style={{
                              backgroundColor: getModuleColor(dot.module),
                              color: 'white',
                            }}
                          >
                            {getModuleLabel(dot.module)}
                          </Badge>
                        </TableCell>
                        <TableCell className="text-muted-foreground truncate max-w-[200px]">
                          {dot.description || '-'}
                        </TableCell>
                        <TableCell className="text-sm text-muted-foreground">
                          {dot.created_at ? new Date(dot.created_at).toLocaleDateString() : '-'}
                        </TableCell>
                        <TableCell>
                          <div className="flex gap-2">
                            <Tooltip>
                              <TooltipTrigger asChild>
                                <Button
                                  variant="ghost"
                                  size="icon"
                                  onClick={() => fetchDotUsage(dot.id)}
                                >
                                  <Info className="h-4 w-4" />
                                </Button>
                              </TooltipTrigger>
                              <TooltipContent>View Usage</TooltipContent>
                            </Tooltip>
                            <Tooltip>
                              <TooltipTrigger asChild>
                                <Button
                                  variant="ghost"
                                  size="icon"
                                  onClick={() => openEditDialogWithDot(dot)}
                                >
                                  <Edit className="h-4 w-4" />
                                </Button>
                              </TooltipTrigger>
                              <TooltipContent>Edit</TooltipContent>
                            </Tooltip>
                            <Tooltip>
                              <TooltipTrigger asChild>
                                <Button
                                  variant="ghost"
                                  size="icon"
                                  onClick={() => openDeleteDialogWithDot(dot)}
                                >
                                  <Trash2 className="h-4 w-4 text-destructive" />
                                </Button>
                              </TooltipTrigger>
                              <TooltipContent>Delete</TooltipContent>
                            </Tooltip>
                          </div>
                        </TableCell>
                      </TableRow>
                    ))
                  )}
                </TableBody>
              </Table>
              <div className="flex items-center justify-between px-4 py-3 border-t">
                <div className="text-sm text-muted-foreground">
                  Showing {page * rowsPerPage + 1} to {Math.min((page + 1) * rowsPerPage, totalCount)} of {totalCount} DOTs
                </div>
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setPage(Math.max(0, page - 1))}
                    disabled={page === 0}
                  >
                    Previous
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setPage(page + 1)}
                    disabled={(page + 1) * rowsPerPage >= totalCount}
                  >
                    Next
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Tab 1: Module Summary */}
        <TabsContent value="summary" className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {moduleSummary.map((summary) => (
              <Card key={summary.module || 'null'}>
                <CardHeader>
                  <div className="flex items-center gap-3">
                    <div
                      className="w-10 h-10 rounded"
                      style={{ backgroundColor: getModuleColor(summary.module) }}
                    />
                    <div>
                      <CardTitle>{getModuleLabel(summary.module)}</CardTitle>
                      <CardDescription>
                        {summary.count} DOT{summary.count !== 1 ? 's' : ''}
                      </CardDescription>
                    </div>
                  </div>
                </CardHeader>
                <Separator />
                <CardContent className="pt-4">
                  <div className="space-y-2 max-h-[300px] overflow-auto">
                    {summary.dots.map((dot) => (
                      <div
                        key={dot.id}
                        className="p-3 rounded-lg bg-muted flex justify-between items-center"
                      >
                        <div>
                          <p className="font-medium text-sm">{dot.name}</p>
                          <p className="text-xs text-muted-foreground">ID: {dot.id}</p>
                        </div>
                        <div className="flex gap-1">
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-8 w-8"
                            onClick={() => fetchDotUsage(dot.id)}
                          >
                            <Info className="h-4 w-4" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-8 w-8"
                            onClick={() => openEditDialogWithDot(dot)}
                          >
                            <Edit className="h-4 w-4" />
                          </Button>
                        </div>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </TabsContent>
      </Tabs>

      {/* Create/Edit Dialog */}
      <Dialog open={openCreateDialog || openEditDialog} onOpenChange={(open) => {
        if (!open) {
          setOpenCreateDialog(false);
          setOpenEditDialog(false);
          resetForm();
        }
      }}>
        <DialogContent className="sm:max-w-[500px]">
          <DialogHeader>
            <DialogTitle>{openEditDialog ? 'Edit DOT' : 'Create New DOT'}</DialogTitle>
            <DialogDescription>
              {openEditDialog ? 'Update the DOT information' : 'Create a new DOT region'}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="name">DOT Name</Label>
              <Input
                id="name"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                placeholder="Enter DOT name"
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="module">Module</Label>
              <Select
                value={formData.module || ''}
                onValueChange={(value) => setFormData({ ...formData, module: value || null })}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select module" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="">Global (All Modules)</SelectItem>
                  {MODULES.filter(m => m.value !== null).map((module) => (
                    <SelectItem key={module.value} value={module.value || ''}>
                      {module.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="description">Description</Label>
              <textarea
                id="description"
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                className="flex min-h-[80px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
                placeholder="Enter description (optional)"
                rows={3}
              />
            </div>
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => {
                setOpenCreateDialog(false);
                setOpenEditDialog(false);
                resetForm();
              }}
            >
              Cancel
            </Button>
            <Button
              onClick={openEditDialog ? handleUpdateDot : handleCreateDot}
            >
              {openEditDialog ? 'Update' : 'Create'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Dialog */}
      <Dialog open={openDeleteDialog} onOpenChange={setOpenDeleteDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete DOT</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete <strong>{editingDot?.name}</strong>?
            </DialogDescription>
          </DialogHeader>
          {dotUsageStats && (
            <div className="space-y-4 py-4">
              {!dotUsageStats.can_delete && (
                <Alert variant="destructive">
                  <AlertTitle>Cannot delete this DOT</AlertTitle>
                  <AlertDescription>
                    <p className="mb-2">The following blockers exist:</p>
                    <ul className="list-disc list-inside space-y-1">
                      {dotUsageStats.deletion_blockers.map((blocker, idx) => (
                        <li key={idx}>{blocker}</li>
                      ))}
                    </ul>
                  </AlertDescription>
                </Alert>
              )}
              {dotUsageStats.can_delete && (
                <Alert>
                  <Check className="h-4 w-4" />
                  <AlertTitle>Safe to delete</AlertTitle>
                  <AlertDescription>
                    This DOT has no associated data and can be safely deleted.
                  </AlertDescription>
                </Alert>
              )}
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setOpenDeleteDialog(false)}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={() => editingDot && handleDeleteDot(editingDot.id)}
              disabled={!dotUsageStats?.can_delete}
            >
              Delete
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Usage Dialog */}
      <Dialog open={openUsageDialog} onOpenChange={setOpenUsageDialog}>
        <DialogContent className="sm:max-w-[500px]">
          <DialogHeader>
            <DialogTitle>DOT Usage Statistics</DialogTitle>
            <DialogDescription>
              Usage statistics for {dotUsageStats?.dot_name}
            </DialogDescription>
          </DialogHeader>
          {dotUsageStats && (
            <div className="space-y-4 py-4">
              <div>
                <Badge
                  style={{
                    backgroundColor: getModuleColor(dotUsageStats.module),
                    color: 'white',
                  }}
                >
                  {getModuleLabel(dotUsageStats.module)}
                </Badge>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <Card>
                  <CardContent className="pt-6 text-center">
                    <h3 className="text-2xl font-bold text-primary">{dotUsageStats.users_count}</h3>
                    <p className="text-xs text-muted-foreground">Users</p>
                  </CardContent>
                </Card>
                <Card>
                  <CardContent className="pt-6 text-center">
                    <h3 className="text-2xl font-bold text-secondary">{dotUsageStats.parks_count}</h3>
                    <p className="text-xs text-muted-foreground">Parks</p>
                  </CardContent>
                </Card>
                <Card>
                  <CardContent className="pt-6 text-center">
                    <h3 className="text-2xl font-bold text-green-600">{dotUsageStats.revenue_records}</h3>
                    <p className="text-xs text-muted-foreground">Revenue Records</p>
                  </CardContent>
                </Card>
                <Card>
                  <CardContent className="pt-6 text-center">
                    <h3 className="text-2xl font-bold text-orange-600">{dotUsageStats.encaissement_records}</h3>
                    <p className="text-xs text-muted-foreground">Encaissement Records</p>
                  </CardContent>
                </Card>
                <Card className="col-span-2">
                  <CardContent className="pt-6 text-center">
                    <h3 className="text-2xl font-bold text-red-600">{dotUsageStats.creance_records}</h3>
                    <p className="text-xs text-muted-foreground">Créance Records</p>
                  </CardContent>
                </Card>
              </div>
              <div>
                {dotUsageStats.can_delete ? (
                  <Alert>
                    <Check className="h-4 w-4" />
                    <AlertTitle>This DOT can be safely deleted</AlertTitle>
                  </Alert>
                ) : (
                  <Alert variant="destructive">
                    <X className="h-4 w-4" />
                    <AlertTitle>Cannot delete - has associated data</AlertTitle>
                  </Alert>
                )}
              </div>
            </div>
          )}
          <DialogFooter>
            <Button onClick={() => setOpenUsageDialog(false)}>Close</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Bulk Update Dialog */}
      <Dialog open={openBulkUpdateDialog} onOpenChange={setOpenBulkUpdateDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Bulk Update DOTs</DialogTitle>
            <DialogDescription>
              Update module for {selectedDots.length} selected DOT(s)
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="bulk-module">New Module</Label>
              <Select
                value={bulkUpdateModule || ''}
                onValueChange={(value) => setBulkUpdateModule(value || null)}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select module" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="">Global (All Modules)</SelectItem>
                  {MODULES.filter(m => m.value !== null).map((module) => (
                    <SelectItem key={module.value} value={module.value || ''}>
                      {module.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setOpenBulkUpdateDialog(false)}>
              Cancel
            </Button>
            <Button onClick={handleBulkUpdate}>
              Update
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default DOTManagementPage;
