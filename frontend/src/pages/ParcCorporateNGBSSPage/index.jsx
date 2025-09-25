import React, { useState, useEffect } from "react";
import { etlAPI } from "../../services/api";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "../../components/ui/card";
import { Button } from "../../components/ui/button";
import { Badge } from "../../components/ui/badge";
import { Input } from "../../components/ui/input";
import { Label } from "../../components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../../components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "../../components/ui/table";
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "../../components/ui/tabs";
import {
  Upload,
  Download,
  BarChart3,
  PieChart,
  Building2,
  FileText,
  AlertCircle,
  CheckCircle,
  Clock,
  Filter,
  Search,
  RefreshCw,
  Eye,
  Network,
} from "lucide-react";
import { toast } from "sonner";
import { handleApiError } from "../../lib/error-handler";
import {
  SimpleBarChart,
  SimplePieChart,
} from "../../components/ui/charts/SimpleChart";

const ParcCorporateNGBSSPage = () => {
  const [overview, setOverview] = useState({});
  const [dotData, setDotData] = useState({});
  const [telecomData, setTelecomData] = useState({});
  const [customerL2Data, setCustomerL2Data] = useState({});
  const [customerL3Data, setCustomerL3Data] = useState({});
  const [previewData, setPreviewData] = useState({});

  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [selectedFiles, setSelectedFiles] = useState([]);
  const [activeTab, setActiveTab] = useState("overview");
  const [lastProcessedFile, setLastProcessedFile] = useState("");

  // Filters
  const [filters, setFilters] = useState({
    dot: "all",
    actel: "all",
    subscriber: "all",
  });
  const [searchTerm, setSearchTerm] = useState("");

  // Process Parc Corporate NGBSS files
  const handleFileUpload = async () => {
    if (!selectedFiles || selectedFiles.length === 0) {
      toast.error("Please select files to upload");
      return;
    }

    setUploading(true);
    const formData = new FormData();

    selectedFiles.forEach(file => {
      formData.append("files", file);
    });

    try {
      const response = await etlAPI.processParcCorporateNGBSS(formData);

      if (response.success) {
        toast.success(
          `ETL Processing completed successfully! Processed ${response.output_records} records.`
        );

        // Store the output file path for data viewing
        if (response.output_files && response.output_files.length > 0) {
          setLastProcessedFile(response.output_files[0]);
          await loadDataViews(response.output_files[0]);
        }

        setSelectedFiles([]);
        const fileInput = document.querySelector('input[type="file"]');
        if (fileInput) fileInput.value = '';
      } else {
        toast.error("ETL processing failed");
      }
    } catch (error) {
      handleApiError(error, "Failed to process Parc Corporate NGBSS files");
    } finally {
      setUploading(false);
    }
  };

  // Load data views from processed file
  const loadDataViews = async (filePath) => {
    if (!filePath) return;

    setLoading(true);
    try {
      // Load all views in parallel
      const [overviewRes, dotRes, telecomRes, l2Res, l3Res, previewRes] = await Promise.all([
        etlAPI.getParcCorporateDataViews(filePath, "overview", filters),
        etlAPI.getParcCorporateDataViews(filePath, "by_dot", filters),
        etlAPI.getParcCorporateDataViews(filePath, "by_telecom_type", filters),
        etlAPI.getParcCorporateDataViews(filePath, "by_customer_l2", filters),
        etlAPI.getParcCorporateDataViews(filePath, "by_customer_l3", filters),
        etlAPI.getParcCorporateDataViews(filePath, "preview_data", filters),
      ]);

      setOverview(overviewRes);
      setDotData(dotRes);
      setTelecomData(telecomRes);
      setCustomerL2Data(l2Res);
      setCustomerL3Data(l3Res);
      setPreviewData(previewRes);
    } catch (error) {
      handleApiError(error, "Failed to load data views");
    } finally {
      setLoading(false);
    }
  };

  // Apply filters
  const applyFilters = () => {
    if (lastProcessedFile) {
      loadDataViews(lastProcessedFile);
    }
  };

  const formatNumber = (num) => {
    return new Intl.NumberFormat().format(num);
  };

  const prepareChartData = (data, labelKey, valueKey) => {
    if (!data || typeof data !== 'object') return [];

    return Object.entries(data).map(([key, value]) => ({
      label: key.length > 15 ? key.substring(0, 15) + '...' : key,
      value: typeof value === 'object' ? value[valueKey] || value.subscriber_count || 0 : value,
    })).slice(0, 10); // Limit to top 10
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold">Parc Corporate NGBSS</h1>
          <p className="text-gray-600 mt-1">
            Algérie Télécom Corporate Subscriber Data Processing & Analytics
          </p>
        </div>

        {lastProcessedFile && (
          <Button
            onClick={() => loadDataViews(lastProcessedFile)}
            disabled={loading}
            variant="outline"
          >
            <RefreshCw className="w-4 h-4 mr-2" />
            Refresh Data
          </Button>
        )}
      </div>

      {/* File Upload Section */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Upload className="w-5 h-5" />
            Upload & Process Files
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <Label htmlFor="files">Select Parc Corporate NGBSS Files (CSV/Excel)</Label>
            <Input
              id="files"
              type="file"
              multiple
              accept=".csv,.xlsx,.xls"
              onChange={(e) => setSelectedFiles(Array.from(e.target.files))}
              className="mt-1"
            />
            {selectedFiles.length > 0 && (
              <div className="mt-2 space-y-1">
                {selectedFiles.map((file, index) => (
                  <Badge key={index} variant="secondary">
                    {file.name}
                  </Badge>
                ))}
              </div>
            )}
          </div>

          <div className="flex gap-2">
            <Button
              onClick={handleFileUpload}
              disabled={uploading || selectedFiles.length === 0}
              className="flex items-center gap-2"
            >
              {uploading ? (
                <>
                  <Clock className="w-4 h-4 animate-spin" />
                  Processing...
                </>
              ) : (
                <>
                  <Upload className="w-4 h-4" />
                  Process Files
                </>
              )}
            </Button>
          </div>

          {/* Business Rules Info */}
          <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg">
            <h4 className="font-medium text-blue-900 mb-2">Applied Business Rules:</h4>
            <ul className="text-sm text-blue-800 space-y-1">
              <li>• DOT Mapping: 2B|HASSI MESSAOUD → DOT OUARGLA</li>
              <li>• DOT Mapping: 99|Grand Compte → DOT SIEGE</li>
              <li>• Filters: Customer L3 categories 5, 57 removed</li>
              <li>• Filters: Predeactivated subscribers removed</li>
              <li>• Filters: Supplementary offers removed</li>
              <li>• Anomaly Detection: Moohtarif patterns flagged</li>
            </ul>
          </div>
        </CardContent>
      </Card>

      {/* Filters Section */}
      {lastProcessedFile && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Filter className="w-5 h-5" />
              Data Filters
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div>
                <Label>DOT Filter</Label>
                <Select value={filters.dot} onValueChange={(value) => setFilters({...filters, dot: value})}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All DOTs</SelectItem>
                    <SelectItem value="OUARGLA">DOT OUARGLA</SelectItem>
                    <SelectItem value="SIEGE">DOT SIEGE</SelectItem>
                    <SelectItem value="CONSTANTINE">DOT CONSTANTINE</SelectItem>
                    <SelectItem value="ALGER">DOT ALGER</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div>
                <Label>Actel Code Filter</Label>
                <Input
                  placeholder="Filter by Actel Code"
                  value={filters.actel}
                  onChange={(e) => setFilters({...filters, actel: e.target.value})}
                />
              </div>

              <div>
                <Label>Subscriber Status</Label>
                <Select value={filters.subscriber} onValueChange={(value) => setFilters({...filters, subscriber: value})}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Status</SelectItem>
                    <SelectItem value="Active">Active</SelectItem>
                    <SelectItem value="Inactive">Inactive</SelectItem>
                    <SelectItem value="Suspended">Suspended</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="flex items-end">
                <Button onClick={applyFilters} disabled={loading}>
                  <Search className="w-4 h-4 mr-2" />
                  Apply Filters
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Data Views Tabs */}
      {lastProcessedFile && (
        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList className="grid w-full grid-cols-6">
            <TabsTrigger value="overview">Overview</TabsTrigger>
            <TabsTrigger value="by_dot">By DOT</TabsTrigger>
            <TabsTrigger value="by_telecom">By Telecom Type</TabsTrigger>
            <TabsTrigger value="by_customer_l2">Customer L2</TabsTrigger>
            <TabsTrigger value="by_customer_l3">Customer L3</TabsTrigger>
            <TabsTrigger value="preview_data">Preview Data</TabsTrigger>
          </TabsList>

          {/* Overview Tab */}
          <TabsContent value="overview" className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
              <Card>
                <CardContent className="p-6">
                  <div className="flex items-center gap-2">
                    <Building2 className="w-8 h-8 text-blue-600" />
                    <div>
                      <p className="text-sm text-gray-600">Total Records</p>
                      <p className="text-2xl font-bold">{formatNumber(overview.total_records || 0)}</p>
                    </div>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardContent className="p-6">
                  <div className="flex items-center gap-2">
                    <Network className="w-8 h-8 text-green-600" />
                    <div>
                      <p className="text-sm text-gray-600">Unique DOTs</p>
                      <p className="text-2xl font-bold">{formatNumber(overview.unique_dots || 0)}</p>
                    </div>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardContent className="p-6">
                  <div className="flex items-center gap-2">
                    <FileText className="w-8 h-8 text-orange-600" />
                    <div>
                      <p className="text-sm text-gray-600">Actel Codes</p>
                      <p className="text-2xl font-bold">{formatNumber(overview.unique_actel_codes || 0)}</p>
                    </div>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardContent className="p-6">
                  <div className="flex items-center gap-2">
                    <BarChart3 className="w-8 h-8 text-purple-600" />
                    <div>
                      <p className="text-sm text-gray-600">Customer L2</p>
                      <p className="text-2xl font-bold">{formatNumber(overview.unique_customer_l2 || 0)}</p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>

            {/* Status and Telecom Type Distribution Charts */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <Card>
                <CardHeader>
                  <CardTitle>Subscriber Status Distribution</CardTitle>
                </CardHeader>
                <CardContent>
                  <SimplePieChart
                    data={prepareChartData(overview.status_distribution)}
                    width={400}
                    height={300}
                  />
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>Telecom Type Distribution</CardTitle>
                </CardHeader>
                <CardContent>
                  <SimpleBarChart
                    data={prepareChartData(overview.telecom_type_distribution)}
                    width={400}
                    height={300}
                  />
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          {/* By DOT Tab */}
          <TabsContent value="by_dot" className="space-y-6">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <Card>
                <CardHeader>
                  <CardTitle>Subscribers by DOT</CardTitle>
                </CardHeader>
                <CardContent>
                  <SimpleBarChart
                    data={prepareChartData(dotData.data, 'dot', 'subscriber_count')}
                    width={500}
                    height={400}
                  />
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>DOT Statistics</CardTitle>
                </CardHeader>
                <CardContent>
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>DOT</TableHead>
                        <TableHead>Subscribers</TableHead>
                        <TableHead>Customer L2</TableHead>
                        <TableHead>Customer L3</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {dotData.data && Object.entries(dotData.data).slice(0, 10).map(([dot, stats]) => (
                        <TableRow key={dot}>
                          <TableCell className="font-medium">{dot}</TableCell>
                          <TableCell>{formatNumber(stats.subscriber_count || 0)}</TableCell>
                          <TableCell>{formatNumber(stats.code_customer_l2 || 0)}</TableCell>
                          <TableCell>{formatNumber(stats.code_customer_l3 || 0)}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          {/* By Telecom Type Tab */}
          <TabsContent value="by_telecom" className="space-y-6">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <Card>
                <CardHeader>
                  <CardTitle>Telecom Type Distribution</CardTitle>
                </CardHeader>
                <CardContent>
                  <SimplePieChart
                    data={prepareChartData(telecomData.data, 'type', 'subscriber_count')}
                    width={400}
                    height={350}
                  />
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>Telecom Type Details</CardTitle>
                </CardHeader>
                <CardContent>
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Telecom Type</TableHead>
                        <TableHead>Subscribers</TableHead>
                        <TableHead>Unique DOTs</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {telecomData.data && Object.entries(telecomData.data).map(([type, stats]) => (
                        <TableRow key={type}>
                          <TableCell className="font-medium">{type}</TableCell>
                          <TableCell>{formatNumber(stats.subscriber_count || 0)}</TableCell>
                          <TableCell>{formatNumber(stats.dot || 0)}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          {/* Customer L2 Tab */}
          <TabsContent value="by_customer_l2" className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>Top Customer L2 Codes</CardTitle>
                <p className="text-sm text-gray-600">
                  Showing top {Object.keys(customerL2Data.top_codes || {}).length} Customer L2 codes by subscriber count
                </p>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  <SimpleBarChart
                    data={prepareChartData(customerL2Data.top_codes)}
                    width={500}
                    height={400}
                  />
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Customer L2 Code</TableHead>
                        <TableHead>Subscriber Count</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {customerL2Data.top_codes && Object.entries(customerL2Data.top_codes).slice(0, 15).map(([code, count]) => (
                        <TableRow key={code}>
                          <TableCell className="font-medium">{code}</TableCell>
                          <TableCell>{formatNumber(count)}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Customer L3 Tab */}
          <TabsContent value="by_customer_l3" className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>Top Customer L3 Codes</CardTitle>
                <p className="text-sm text-gray-600">
                  Showing top {Object.keys(customerL3Data.top_codes || {}).length} Customer L3 codes by subscriber count
                </p>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                  <SimpleBarChart
                    data={prepareChartData(customerL3Data.top_codes)}
                    width={500}
                    height={400}
                  />
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Customer L3 Code</TableHead>
                        <TableHead>Subscriber Count</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {customerL3Data.top_codes && Object.entries(customerL3Data.top_codes).slice(0, 15).map(([code, count]) => (
                        <TableRow key={code}>
                          <TableCell className="font-medium">{code}</TableCell>
                          <TableCell>{formatNumber(count)}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* Preview Data Tab */}
          <TabsContent value="preview_data" className="space-y-6">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Eye className="w-5 h-5" />
                  Data Preview
                </CardTitle>
                <p className="text-sm text-gray-600">
                  Showing {previewData.showing || 0} of {formatNumber(previewData.total_records || 0)} records
                </p>
              </CardHeader>
              <CardContent>
                <div className="overflow-x-auto">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        {previewData.columns && previewData.columns.slice(0, 8).map((col) => (
                          <TableHead key={col}>{col}</TableHead>
                        ))}
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {previewData.data && previewData.data.slice(0, 20).map((row, index) => (
                        <TableRow key={index}>
                          {previewData.columns && previewData.columns.slice(0, 8).map((col) => (
                            <TableCell key={col}>
                              {row[col] !== null && row[col] !== undefined ? String(row[col]).substring(0, 50) : '-'}
                            </TableCell>
                          ))}
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      )}

      {/* No Data State */}
      {!lastProcessedFile && !uploading && (
        <Card>
          <CardContent className="p-12 text-center">
            <Building2 className="w-16 h-16 text-gray-400 mx-auto mb-4" />
            <h3 className="text-xl font-semibold text-gray-600 mb-2">
              No Parc Corporate Data Available
            </h3>
            <p className="text-gray-500 mb-6">
              Upload and process your Parc Corporate NGBSS files to view analytics and insights
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  );
};

export default ParcCorporateNGBSSPage;