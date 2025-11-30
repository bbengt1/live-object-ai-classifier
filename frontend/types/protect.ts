/**
 * TypeScript types for UniFi Protect controller integration
 * Story P2-1.3: Controller Configuration UI
 */

/**
 * Protect controller as returned by the API (read operations)
 */
export interface IProtectController {
  id: string;
  name: string;
  host: string;
  port: number;
  username: string;
  verify_ssl: boolean;
  is_connected: boolean;
  last_connected_at: string | null;
  last_error: string | null;
  created_at: string;
  updated_at: string;
}

/**
 * Create controller request payload
 */
export interface IProtectControllerCreate {
  name: string;
  host: string;
  port?: number;
  username: string;
  password: string;
  verify_ssl?: boolean;
}

/**
 * Update controller request payload (all fields optional)
 */
export interface IProtectControllerUpdate {
  name?: string;
  host?: string;
  port?: number;
  username?: string;
  password?: string;
  verify_ssl?: boolean;
}

/**
 * Test connection request payload (no name required)
 */
export interface IProtectControllerTest {
  host: string;
  port?: number;
  username: string;
  password: string;
  verify_ssl?: boolean;
}

/**
 * Connection test result data
 */
export interface IProtectTestResultData {
  success: boolean;
  message: string;
  firmware_version?: string;
  camera_count?: number;
}

/**
 * Standard API meta response
 */
export interface IProtectMetaResponse {
  request_id: string;
  timestamp: string;
  count?: number;
}

/**
 * Single controller response with meta
 */
export interface IProtectControllerSingleResponse {
  data: IProtectController;
  meta: IProtectMetaResponse;
}

/**
 * List of controllers response with meta
 */
export interface IProtectControllerListResponse {
  data: IProtectController[];
  meta: IProtectMetaResponse;
}

/**
 * Connection test response with meta
 */
export interface IProtectTestResponse {
  data: IProtectTestResultData;
  meta: IProtectMetaResponse;
}

/**
 * Delete response
 */
export interface IProtectControllerDeleteResponse {
  data: { deleted: boolean };
  meta: IProtectMetaResponse;
}

/**
 * Connection status for UI display
 */
export type ConnectionStatus = 'not_configured' | 'connecting' | 'connected' | 'error';
