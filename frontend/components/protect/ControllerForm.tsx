/**
 * UniFi Protect Controller Form Component
 * Story P2-1.3: Controller Configuration UI
 *
 * Form for adding a new UniFi Protect controller with:
 * - Name, Host, Username, Password, Verify SSL fields
 * - Test Connection button
 * - Save button (enabled after successful test)
 * - Real-time validation on blur
 */

'use client';

import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { useMutation } from '@tanstack/react-query';
import { toast } from 'sonner';
import { Loader2, CheckCircle2, XCircle, Shield } from 'lucide-react';

import { apiClient, ApiError } from '@/lib/api-client';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Switch } from '@/components/ui/switch';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { ConnectionStatus, type ConnectionStatusType } from './ConnectionStatus';

// Zod schema matching backend validation
const controllerFormSchema = z.object({
  name: z
    .string()
    .min(1, 'Name is required')
    .max(100, 'Name must be 100 characters or less'),
  host: z
    .string()
    .min(1, 'Host is required')
    .max(255, 'Host must be 255 characters or less'),
  port: z
    .number()
    .int()
    .min(1, 'Port must be between 1 and 65535')
    .max(65535, 'Port must be between 1 and 65535'),
  username: z
    .string()
    .min(1, 'Username is required')
    .max(100, 'Username must be 100 characters or less'),
  password: z
    .string()
    .min(1, 'Password is required')
    .max(100, 'Password must be 100 characters or less'),
  verify_ssl: z.boolean(),
});

type ControllerFormData = z.infer<typeof controllerFormSchema>;

interface ControllerFormProps {
  onSaveSuccess?: (controller: { id: string; name: string }) => void;
  onCancel?: () => void;
}

export function ControllerForm({ onSaveSuccess, onCancel }: ControllerFormProps) {
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatusType>('not_configured');
  const [testResult, setTestResult] = useState<{
    firmwareVersion?: string;
    cameraCount?: number;
    errorMessage?: string;
  }>({});
  const [connectionTested, setConnectionTested] = useState(false);

  const form = useForm<ControllerFormData>({
    resolver: zodResolver(controllerFormSchema),
    defaultValues: {
      name: '',
      host: '',
      port: 443,
      username: '',
      password: '',
      verify_ssl: false,
    },
    mode: 'onBlur', // Validate on blur per AC7
  });

  const { formState: { errors } } = form;

  // Reset test status when form values change
  const handleFieldChange = () => {
    if (connectionTested) {
      setConnectionTested(false);
      setConnectionStatus('not_configured');
      setTestResult({});
    }
  };

  // Test connection mutation
  const testConnectionMutation = useMutation({
    mutationFn: async (data: ControllerFormData) => {
      return apiClient.protect.testConnection({
        host: data.host,
        port: data.port,
        username: data.username,
        password: data.password,
        verify_ssl: data.verify_ssl,
      });
    },
    onMutate: () => {
      setConnectionStatus('connecting');
      setTestResult({});
    },
    onSuccess: (response) => {
      if (response.data.success) {
        setConnectionStatus('connected');
        setTestResult({
          firmwareVersion: response.data.firmware_version,
          cameraCount: response.data.camera_count,
        });
        setConnectionTested(true);
        toast.success('Connection successful!');
      } else {
        setConnectionStatus('error');
        setTestResult({ errorMessage: response.data.message });
        toast.error(response.data.message || 'Connection failed');
      }
    },
    onError: (error: Error) => {
      setConnectionStatus('error');
      let errorMessage = 'Connection failed';

      if (error instanceof ApiError) {
        // Map HTTP status codes to user-friendly messages
        switch (error.statusCode) {
          case 401:
            errorMessage = 'Authentication failed - check username and password';
            break;
          case 502:
            errorMessage = 'SSL certificate verification failed - try disabling SSL verification';
            break;
          case 503:
            errorMessage = 'Host unreachable - check the IP address or hostname';
            break;
          case 504:
            errorMessage = 'Connection timed out - the controller may be offline';
            break;
          default:
            errorMessage = error.message || 'Connection failed';
        }
      }

      setTestResult({ errorMessage });
      toast.error(errorMessage);
    },
  });

  // Save controller mutation
  const saveControllerMutation = useMutation({
    mutationFn: async (data: ControllerFormData) => {
      return apiClient.protect.createController({
        name: data.name,
        host: data.host,
        port: data.port,
        username: data.username,
        password: data.password,
        verify_ssl: data.verify_ssl,
      });
    },
    onSuccess: (response) => {
      toast.success('Controller saved successfully');
      onSaveSuccess?.({ id: response.data.id, name: response.data.name });
    },
    onError: (error: Error) => {
      let errorMessage = 'Failed to save controller';

      if (error instanceof ApiError) {
        if (error.statusCode === 409) {
          errorMessage = 'A controller with this name already exists';
        } else {
          errorMessage = error.message || errorMessage;
        }
      }

      toast.error(`Failed to save controller: ${errorMessage}`);
    },
  });

  const handleTestConnection = async () => {
    // Validate form first
    const isFormValid = await form.trigger();
    if (!isFormValid) {
      toast.error('Please fix form errors before testing');
      return;
    }

    const data = form.getValues();
    testConnectionMutation.mutate(data);
  };

  const handleSave = async () => {
    const isFormValid = await form.trigger();
    if (!isFormValid) {
      toast.error('Please fix form errors before saving');
      return;
    }

    const data = form.getValues();
    saveControllerMutation.mutate(data);
  };

  const isTestingConnection = testConnectionMutation.isPending;
  const isSaving = saveControllerMutation.isPending;
  const canSave = connectionTested && connectionStatus === 'connected' && !isSaving;

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Shield className="h-5 w-5 text-cyan-500" />
            <CardTitle>Controller Connection</CardTitle>
          </div>
          <ConnectionStatus
            status={connectionStatus}
            errorMessage={testResult.errorMessage}
            firmwareVersion={testResult.firmwareVersion}
            cameraCount={testResult.cameraCount}
          />
        </div>
        <CardDescription>
          Enter your UniFi Protect controller details to connect
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {/* Name Field */}
          <div className="space-y-2">
            <Label htmlFor="controller-name">
              Name <span className="text-red-500">*</span>
            </Label>
            <Input
              id="controller-name"
              placeholder="Home UDM Pro"
              {...form.register('name', { onChange: handleFieldChange })}
              className={errors.name ? 'border-red-500' : ''}
            />
            {errors.name && (
              <p className="text-sm text-red-500">{errors.name.message}</p>
            )}
          </div>

          {/* Host Field */}
          <div className="space-y-2">
            <Label htmlFor="controller-host">
              Host / IP Address <span className="text-red-500">*</span>
            </Label>
            <Input
              id="controller-host"
              placeholder="192.168.1.1 or unifi.local"
              {...form.register('host', { onChange: handleFieldChange })}
              className={errors.host ? 'border-red-500' : ''}
            />
            {errors.host && (
              <p className="text-sm text-red-500">{errors.host.message}</p>
            )}
          </div>

          {/* Port Field */}
          <div className="space-y-2">
            <Label htmlFor="controller-port">Port</Label>
            <Input
              id="controller-port"
              type="number"
              placeholder="443"
              {...form.register('port', {
                valueAsNumber: true,
                onChange: handleFieldChange
              })}
              className={errors.port ? 'border-red-500' : ''}
            />
            {errors.port && (
              <p className="text-sm text-red-500">{errors.port.message}</p>
            )}
          </div>

          {/* Username Field */}
          <div className="space-y-2">
            <Label htmlFor="controller-username">
              Username <span className="text-red-500">*</span>
            </Label>
            <Input
              id="controller-username"
              placeholder="admin"
              autoComplete="username"
              {...form.register('username', { onChange: handleFieldChange })}
              className={errors.username ? 'border-red-500' : ''}
            />
            {errors.username && (
              <p className="text-sm text-red-500">{errors.username.message}</p>
            )}
          </div>

          {/* Password Field */}
          <div className="space-y-2">
            <Label htmlFor="controller-password">
              Password <span className="text-red-500">*</span>
            </Label>
            <Input
              id="controller-password"
              type="password"
              placeholder="••••••••"
              autoComplete="current-password"
              {...form.register('password', { onChange: handleFieldChange })}
              className={errors.password ? 'border-red-500' : ''}
            />
            {errors.password && (
              <p className="text-sm text-red-500">{errors.password.message}</p>
            )}
          </div>

          {/* Verify SSL Checkbox */}
          <div className="flex items-center justify-between p-3 rounded-lg border">
            <div className="flex-1">
              <Label htmlFor="verify-ssl" className="cursor-pointer">
                Verify SSL Certificate
              </Label>
              <p className="text-xs text-muted-foreground">
                Disable if using self-signed certificates (common for local UniFi deployments)
              </p>
            </div>
            <Switch
              id="verify-ssl"
              checked={form.watch('verify_ssl')}
              onCheckedChange={(checked) => {
                form.setValue('verify_ssl', checked);
                handleFieldChange();
              }}
            />
          </div>

          {/* Action Buttons */}
          <div className="flex flex-col sm:flex-row gap-3 pt-4">
            <Button
              type="button"
              variant="outline"
              onClick={handleTestConnection}
              disabled={isTestingConnection || isSaving}
              className="flex-1 bg-cyan-50 hover:bg-cyan-100 border-cyan-200 text-cyan-700"
            >
              {isTestingConnection && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
              {connectionStatus === 'connected' && <CheckCircle2 className="h-4 w-4 mr-2 text-green-600" />}
              {connectionStatus === 'error' && <XCircle className="h-4 w-4 mr-2 text-red-600" />}
              Test Connection
            </Button>

            <Button
              type="button"
              onClick={handleSave}
              disabled={!canSave}
              className="flex-1"
            >
              {isSaving && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
              Save Controller
            </Button>
          </div>

          {/* Help Text */}
          {!connectionTested && (
            <p className="text-xs text-muted-foreground text-center">
              Test the connection before saving to verify your credentials
            </p>
          )}

          {/* Cancel Button (if onCancel provided) */}
          {onCancel && (
            <Button
              type="button"
              variant="ghost"
              onClick={onCancel}
              className="w-full"
              disabled={isSaving}
            >
              Cancel
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
