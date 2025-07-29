import React from "react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "../../components/ui/card";
import { Button } from "../../components/ui/button";
import { Badge } from "../../components/ui/badge";
import { Shield, Lock, CheckCircle, AlertTriangle, Info } from "lucide-react";
import { Label } from "../../components/ui/label";

const ProtectedPage = () => {
  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-gray-900">Protected Content</h1>
        <p className="text-gray-600 mt-2">
          This page is only accessible to authenticated users
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Access Status */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center">
              <Shield className="h-5 w-5 mr-2 text-green-600" />
              Access Status
            </CardTitle>
            <CardDescription>
              Your current authentication status
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center space-x-2">
              <CheckCircle className="h-5 w-5 text-green-600" />
              <span className="font-medium">Authenticated</span>
              <Badge
                variant="secondary"
                className="bg-green-100 text-green-800"
              >
                Active
              </Badge>
            </div>

            <div className="flex items-center space-x-2">
              <Lock className="h-5 w-5 text-blue-600" />
              <span className="font-medium">Session Valid</span>
              <Badge variant="secondary" className="bg-blue-100 text-blue-800">
                Valid
              </Badge>
            </div>

            <div className="flex items-center space-x-2">
              <Shield className="h-5 w-5 text-purple-600" />
              <span className="font-medium">Permissions</span>
              <Badge
                variant="secondary"
                className="bg-purple-100 text-purple-800"
              >
                Granted
              </Badge>
            </div>
          </CardContent>
        </Card>

        {/* Security Information */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center">
              <Info className="h-5 w-5 mr-2 text-blue-600" />
              Security Information
            </CardTitle>
            <CardDescription>Details about your secure session</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label className="text-sm font-medium text-gray-500">
                Session ID
              </Label>
              <p className="text-sm text-gray-900 font-mono">
                sess_abc123def456ghi789
              </p>
            </div>

            <div className="space-y-2">
              <Label className="text-sm font-medium text-gray-500">
                Login Time
              </Label>
              <p className="text-sm text-gray-900">
                December 15, 2023 at 10:30 AM
              </p>
            </div>

            <div className="space-y-2">
              <Label className="text-sm font-medium text-gray-500">
                IP Address
              </Label>
              <p className="text-sm text-gray-900">192.168.1.100</p>
            </div>

            <div className="space-y-2">
              <Label className="text-sm font-medium text-gray-500">
                User Agent
              </Label>
              <p className="text-sm text-gray-900">
                Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36
              </p>
            </div>
          </CardContent>
        </Card>

        {/* Protected Content */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Protected Content Area</CardTitle>
            <CardDescription>
              This content is only visible to authenticated users
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                <div className="flex items-center space-x-2">
                  <CheckCircle className="h-5 w-5 text-green-600" />
                  <span className="font-medium text-green-800">
                    Welcome to the protected area!
                  </span>
                </div>
                <p className="text-green-700 mt-2">
                  You have successfully authenticated and can now access this
                  protected content. This demonstrates that the authentication
                  system is working correctly.
                </p>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <h3 className="font-medium">Available Actions</h3>
                  <ul className="space-y-1 text-sm text-gray-600">
                    <li>• View protected data</li>
                    <li>• Manage user settings</li>
                    <li>• Access admin features</li>
                    <li>• Download reports</li>
                  </ul>
                </div>

                <div className="space-y-2">
                  <h3 className="font-medium">Security Features</h3>
                  <ul className="space-y-1 text-sm text-gray-600">
                    <li>• Session management</li>
                    <li>• Role-based access control</li>
                    <li>• Secure API endpoints</li>
                    <li>• Audit logging</li>
                  </ul>
                </div>
              </div>

              <div className="flex space-x-2">
                <Button variant="outline">View Profile</Button>
                <Button variant="outline">Settings</Button>
                <Button variant="outline">Logout</Button>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Warning */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="flex items-center">
              <AlertTriangle className="h-5 w-5 mr-2 text-yellow-600" />
              Security Notice
            </CardTitle>
            <CardDescription>Important security information</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
              <p className="text-yellow-800 text-sm">
                <strong>Important:</strong> This is a protected page that
                demonstrates authentication and authorization features. In a
                production environment, you would implement additional security
                measures such as:
              </p>
              <ul className="text-yellow-700 text-sm mt-2 space-y-1">
                <li>• Two-factor authentication (2FA)</li>
                <li>• Rate limiting</li>
                <li>• IP whitelisting</li>
                <li>• Session timeout</li>
                <li>• Audit trails</li>
              </ul>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default ProtectedPage;
