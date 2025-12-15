/**
 * TypeScript type definitions for ONVIF Camera Discovery API
 * Mirrors backend Pydantic schemas from backend/app/schemas/discovery.py
 *
 * Story P5-2.3: Build Camera Discovery UI with Add Action
 */

/**
 * Stream profile from an ONVIF camera.
 * Contains profile name, resolution, frame rate, and RTSP URL.
 */
export interface IStreamProfile {
  /** Profile name (e.g., 'mainStream', 'subStream') */
  name: string;
  /** Profile token used for ONVIF API calls */
  token: string;
  /** Resolution as string (e.g., '1920x1080') */
  resolution: string;
  /** Video width in pixels */
  width: number;
  /** Video height in pixels */
  height: number;
  /** Frame rate (frames per second) */
  fps: number;
  /** RTSP URL for this profile's stream */
  rtsp_url: string;
  /** Video encoding (e.g., 'H264', 'H265', 'JPEG') */
  encoding?: string | null;
}

/**
 * Device information from ONVIF GetDeviceInformation response.
 */
export interface IDeviceInfo {
  /** Device name (from GetDeviceInformation or derived from model) */
  name: string;
  /** Device manufacturer */
  manufacturer: string;
  /** Device model */
  model: string;
  /** Firmware version */
  firmware_version?: string | null;
  /** Device serial number */
  serial_number?: string | null;
  /** Hardware identifier */
  hardware_id?: string | null;
}

/**
 * Basic device discovered via WS-Discovery.
 * Contains minimal information from ProbeMatch responses.
 */
export interface IDiscoveredDevice {
  /** XAddrs service URL from ProbeMatch response */
  endpoint_url: string;
  /** Device scopes (e.g., onvif://www.onvif.org/type/NetworkVideoTransmitter) */
  scopes: string[];
  /** Device types from ProbeMatch (e.g., tdn:NetworkVideoTransmitter) */
  types: string[];
  /** Metadata version from ProbeMatch if available */
  metadata_version?: string | null;
}

/**
 * Full camera details retrieved via ONVIF GetDeviceInformation and GetProfiles.
 * This is the comprehensive model returned when querying a specific device.
 */
export interface IDiscoveredCameraDetails {
  /** Unique identifier for this camera (generated from endpoint URL) */
  id: string;
  /** ONVIF device service URL */
  endpoint_url: string;
  /** IP address extracted from endpoint URL */
  ip_address: string;
  /** Port number extracted from endpoint URL */
  port: number;
  /** Device information from GetDeviceInformation */
  device_info: IDeviceInfo;
  /** Available stream profiles */
  profiles: IStreamProfile[];
  /** Primary/best quality RTSP URL (highest resolution profile) */
  primary_rtsp_url: string;
  /** Whether the device requires authentication for ONVIF queries */
  requires_auth: boolean;
  /** Timestamp when device details were retrieved */
  discovered_at: string;
}

/**
 * Request body for camera discovery endpoint.
 */
export interface IDiscoveryRequest {
  /** Discovery timeout in seconds (default: 10, max: 60) */
  timeout?: number;
}

/**
 * Response from camera discovery endpoint.
 */
export interface IDiscoveryResponse {
  /** Discovery status: 'complete', 'timeout', or 'error' */
  status: 'complete' | 'timeout' | 'error';
  /** Time taken for discovery scan in milliseconds */
  duration_ms: number;
  /** List of discovered ONVIF devices */
  devices: IDiscoveredDevice[];
  /** Number of devices discovered */
  device_count: number;
  /** Error message if status is 'error' */
  error_message?: string | null;
}

/**
 * Response for discovery status check.
 */
export interface IDiscoveryStatusResponse {
  /** Whether ONVIF discovery is available */
  available: boolean;
  /** Whether WSDiscovery is installed */
  library_installed: boolean;
  /** Status message */
  message: string;
}

/**
 * Request to fetch detailed information from a discovered ONVIF device.
 */
export interface IDeviceDetailsRequest {
  /** ONVIF device service URL from discovery */
  endpoint_url: string;
  /** Username for ONVIF authentication (if required) */
  username?: string | null;
  /** Password for ONVIF authentication (if required) */
  password?: string | null;
}

/**
 * Response from device details endpoint.
 */
export interface IDeviceDetailsResponse {
  /** Status: 'success', 'auth_required', or 'error' */
  status: 'success' | 'auth_required' | 'error';
  /** Device details if successful */
  device?: IDiscoveredCameraDetails | null;
  /** Error message if status is 'error' or 'auth_required' */
  error_message?: string | null;
  /** Time taken to query device in milliseconds */
  duration_ms: number;
}

/**
 * Discovery UI state for managing the discovery process
 */
export interface IDiscoveryState {
  /** Whether a discovery scan is in progress */
  isScanning: boolean;
  /** Discovered devices from the scan */
  devices: IDiscoveredDevice[];
  /** Device details (keyed by endpoint_url) */
  deviceDetails: Map<string, IDiscoveredCameraDetails>;
  /** Error message if discovery failed */
  error?: string | null;
  /** Discovery duration in milliseconds */
  duration?: number | null;
}


// ============================================================================
// Story P5-2.4: Test Connection Types
// ============================================================================


/**
 * Request to test an RTSP connection without saving the camera.
 */
export interface ITestConnectionRequest {
  /** RTSP URL to test (must start with rtsp:// or rtsps://) */
  rtsp_url: string;
  /** Username for RTSP authentication (if required) */
  username?: string | null;
  /** Password for RTSP authentication (if required) */
  password?: string | null;
}

/**
 * Response from RTSP connection test endpoint.
 */
export interface ITestConnectionResponse {
  /** Whether the connection test was successful */
  success: boolean;
  /** Time to establish connection and receive first frame (ms) */
  latency_ms?: number | null;
  /** Video resolution (e.g., '1920x1080') */
  resolution?: string | null;
  /** Frame rate (frames per second) */
  fps?: number | null;
  /** Video codec (e.g., 'H.264', 'H.265') */
  codec?: string | null;
  /** Error message if test failed */
  error?: string | null;
}
