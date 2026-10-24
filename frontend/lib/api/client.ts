// lib/api/client.ts — the ONLY place the frontend calls fetch (required, copy as-is)
import type {
  ApiRoutes,
  ApiRouteKey,
  ApiResponse,
  ClientErrorCode,
  ScanMode,
  ScanStage,
  SonicScanResult,
  UUID,
} from "./types";

export const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "";
const TOKEN_KEY = "fp_access_token";

export class ApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly code: ClientErrorCode,
    message: string,
    public readonly details: Record<string, unknown> = {},
  ) {
    super(message);
  }
}

export const tokenStore = {
  get: (): string | null => {
    try {
      return typeof window === "undefined"
        ? null
        : window.localStorage.getItem(TOKEN_KEY);
    } catch {
      return null;
    }
  },
  set: (t: string): void => {
    try {
      window.localStorage.setItem(TOKEN_KEY, t);
    } catch {
      /* storage unavailable */
    }
  },
  clear: (): void => {
    try {
      window.localStorage.removeItem(TOKEN_KEY);
    } catch {
      /* storage unavailable */
    }
  },
};

type ParamNames<K extends string> =
  K extends `${string}:${infer P}/${infer Rest}`
    ? P | ParamNames<`/${Rest}`>
    : K extends `${string}:${infer P}`
      ? P
      : never;
type PathParams<K extends string> = [ParamNames<K>] extends [never]
  ? Record<string, never>
  : Record<ParamNames<K>, string>;

export type CallArgs<K extends ApiRouteKey> = {
  params?: PathParams<K>;
  query?: ApiRoutes[K]["query"] extends null
    ? undefined
    : ApiRoutes[K]["query"];
  body?: ApiRoutes[K]["body"] extends null
    ? undefined
    : ApiRoutes[K]["body"] extends "multipart"
      ? FormData
      : ApiRoutes[K]["body"];
};

/** Mock mode (NEXT_PUBLIC_USE_MOCKS=true): lib/api/mock.ts registers a handler that returns typed fixtures
 *  or throws ApiError with a real ErrorCode. Components never know whether mocks are on. */
export type MockHandler = <K extends ApiRouteKey>(
  key: K,
  args: CallArgs<K>,
) => Promise<ApiRoutes[K]["res"]>;
let mockHandler: MockHandler | null = null;
export function setMockHandler(handler: MockHandler | null): void {
  mockHandler = handler;
}

/** Typed call: api("POST /pools/:poolId/reservations", { params: { poolId }, body: { batchId } }) */
export async function api<K extends ApiRouteKey>(
  key: K,
  args: CallArgs<K> = {},
): Promise<ApiRoutes[K]["res"]> {
  if (mockHandler && process.env.NEXT_PUBLIC_USE_MOCKS === "true")
    return mockHandler(key, args);
  const [method, template] = key.split(" ") as [string, string];
  let path = template;
  for (const [k, v] of Object.entries(
    (args.params ?? {}) as Record<string, string>,
  ))
    path = path.replace(`:${k}`, encodeURIComponent(v));
  const qs = new URLSearchParams();
  for (const [k, v] of Object.entries(
    (args.query ?? {}) as Record<string, unknown>,
  ))
    if (v !== undefined && v !== null) qs.set(k, String(v));
  const url = `${API_BASE_URL}/api/v1${path}${qs.toString() ? `?${qs}` : ""}`;

  const headers = new Headers();
  const token = tokenStore.get();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  let body: BodyInit | undefined;
  if (args.body instanceof FormData)
    body = args.body; // browser sets multipart boundary itself
  else if (args.body !== undefined) {
    headers.set("Content-Type", "application/json");
    body = JSON.stringify(args.body);
  }

  let res: Response;
  try {
    res = await fetch(url, { method, headers, body });
  } catch {
    throw new ApiError(
      0,
      "NETWORK_ERROR",
      "Cannot reach the server. Check your connection.",
    );
  }

  let json: ApiResponse<ApiRoutes[K]["res"]>;
  try {
    json = (await res.json()) as ApiResponse<ApiRoutes[K]["res"]>;
  } catch {
    throw new ApiError(
      res.status,
      "INVALID_RESPONSE",
      "Server returned a non-JSON response.",
    );
  }

  if (json.success) return json.data;
  if (res.status === 401) tokenStore.clear();
  throw new ApiError(
    res.status,
    json.error.code,
    json.error.message,
    json.error.details,
  );
}

/** Builds the multipart body for POST /assay/sonic-scans. Omit optional fields instead of sending "null". */
export function buildSonicScanForm(input: {
  wav: Blob;
  batchId: UUID;
  stage: ScanStage;
  mode: ScanMode;
  clientScanId: UUID;
  recordedAt: string;
  phoneModel: string | null;
  avgFruitMassG: number | null;
}): FormData {
  const fd = new FormData();
  fd.append("audio", input.wav, "scan.wav");
  fd.append("batchId", input.batchId);
  fd.append("stage", input.stage);
  fd.append("mode", input.mode);
  fd.append("clientScanId", input.clientScanId);
  fd.append("recordedAt", input.recordedAt);
  if (input.phoneModel !== null) fd.append("phoneModel", input.phoneModel);
  if (input.avgFruitMassG !== null)
    fd.append("avgFruitMassG", String(input.avgFruitMassG));
  return fd;
}

/** 16-bit PCM mono WAV encoder for Float32 samples captured via AudioWorklet. Never upload MediaRecorder webm/mp4. */
export function encodeWav(
  samples: Float32Array,
  sampleRate: 44100 | 48000,
): Blob {
  const buf = new ArrayBuffer(44 + samples.length * 2);
  const v = new DataView(buf);
  const w = (o: number, s: string) => {
    for (let i = 0; i < s.length; i++) v.setUint8(o + i, s.charCodeAt(i));
  };
  w(0, "RIFF");
  v.setUint32(4, 36 + samples.length * 2, true);
  w(8, "WAVE");
  w(12, "fmt ");
  v.setUint32(16, 16, true);
  v.setUint16(20, 1, true);
  v.setUint16(22, 1, true);
  v.setUint32(24, sampleRate, true);
  v.setUint32(28, sampleRate * 2, true);
  v.setUint16(32, 2, true);
  v.setUint16(34, 16, true);
  w(36, "data");
  v.setUint32(40, samples.length * 2, true);
  for (let i = 0; i < samples.length; i++) {
    const s = Math.max(-1, Math.min(1, samples[i]));
    v.setInt16(44 + i * 2, s < 0 ? s * 0x8000 : s * 0x7fff, true);
  }
  return new Blob([buf], { type: "audio/wav" });
}

/** Example (type-checks): */
export async function uploadScan(
  wav: Blob,
  batchId: UUID,
): Promise<SonicScanResult> {
  return api("POST /assay/sonic-scans", {
    body: buildSonicScanForm({
      wav,
      batchId,
      stage: "FARM_GATE",
      mode: "TAP",
      clientScanId: crypto.randomUUID(),
      recordedAt: new Date().toISOString().replace(/\.\d{3}Z$/, "Z"),
      phoneModel: null,
      avgFruitMassG: null,
    }),
  });
}
