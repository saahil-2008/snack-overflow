// FarmPool 360 x ChronoCrop — API contract types (v1.1.0)
// Frontend copy: lib/api/types.ts. Generated from PRD Section 5. Do not edit by hand.
// Every key is camelCase. "T | null" = key always present, value may be null.
// "key?: T" (omittable) appears ONLY in: UpdateProfileRequest (PATCH), SonicScanFormFields
// (optional multipart fields) and ApiRoutes query objects (optional query params).

// ───────────────────────── Primitives ─────────────────────────
/** RFC 4122 UUID v4, lowercase, hyphenated. Example: "3f2b8c1e-9a4d-4c2b-8f1e-2d7a6b5c4e3f" */
export type UUID = string;
/** ISO 8601 UTC, seconds precision, trailing Z. Example: "2026-10-24T12:00:00Z" */
export type IsoDateTime = string;

// ───────────────────────── Enums ─────────────────────────
export const ROLES = ["FARMER", "LOGISTICS", "BUYER", "ADMIN"] as const;
export type Role = (typeof ROLES)[number];
export type RegisterRole = Exclude<Role, "ADMIN">;

export const LANGUAGES = ["EN", "HI", "MR", "TA"] as const;
export type Language = (typeof LANGUAGES)[number];

export const THEMES = ["LIGHT", "DARK", "SYSTEM"] as const;
export type Theme = (typeof THEMES)[number];

export const ETHYLENE_CLASSES = ["EMITTER", "SENSITIVE", "NEUTRAL"] as const;
export type EthyleneClass = (typeof ETHYLENE_CLASSES)[number];

export const RECOMMENDATIONS = [
  "HARVEST_NOW",
  "RECHECK_TOMORROW",
  "WAIT_48H",
] as const;
export type Recommendation = (typeof RECOMMENDATIONS)[number];

export const ADVISORY_REASON_CODES = [
  "OVERMATURE",
  "MATURE_WEATHER_RISK",
  "MATURE_PICKUP_SOON",
  "NEAR_MATURE_RECHECK",
  "IMMATURE_WAIT",
] as const;
export type AdvisoryReasonCode = (typeof ADVISORY_REASON_CODES)[number];

export const WEATHER_RISKS = ["LOW", "MEDIUM", "HIGH"] as const;
export type WeatherRisk = (typeof WEATHER_RISKS)[number];

export const BATCH_STATUSES = [
  "PENDING_ASSAY",
  "GRADED",
  "POOLED",
  "IN_TRANSIT",
  "ARRIVED",
] as const;
export type BatchStatus = (typeof BATCH_STATUSES)[number];

export const QUALITY_GRADES = ["A", "B", "C"] as const;
export type QualityGrade = (typeof QUALITY_GRADES)[number];

export const SCAN_STAGES = ["FARM_GATE", "LOADING", "INTAKE"] as const;
export type ScanStage = (typeof SCAN_STAGES)[number];

export const SCAN_MODES = ["TAP", "CHIRP"] as const;
export type ScanMode = (typeof SCAN_MODES)[number];

export const ROUTE_TIERS = [
  "FAST_QCOMM",
  "FLEX_REGIONAL",
  "STANDARD_WHOLESALE",
] as const;
export type RouteTier = (typeof ROUTE_TIERS)[number];

export const POOL_STATUSES = ["OPEN", "IN_TRANSIT", "ARRIVED"] as const;
export type PoolStatus = (typeof POOL_STATUSES)[number];

export const COMPATIBILITY_REASONS = [
  "POOL_NOT_OPEN",
  "DISTANCE_EXCEEDED",
  "ETHYLENE_CONFLICT",
  "RUL_OUT_OF_COHORT",
  "ROUTE_TIER_MISMATCH",
  "CAPACITY_EXCEEDED",
] as const;
export type CompatibilityReason = (typeof COMPATIBILITY_REASONS)[number];

export const LISTING_STATUSES = ["ACTIVE", "SOLD_OUT", "WITHDRAWN"] as const;
export type ListingStatus = (typeof LISTING_STATUSES)[number];

export const ORDER_STATUSES = [
  "PLACED",
  "INTAKE_ACCEPTED",
  "INTAKE_FLAGGED",
] as const;
export type OrderStatus = (typeof ORDER_STATUSES)[number];

export const INTAKE_RESULTS = ["ACCEPTED", "FLAGGED"] as const;
export type IntakeResult = (typeof INTAKE_RESULTS)[number];

export const RESPONSIBLE_PARTIES = [
  "FARM",
  "TRANSIT",
  "BUYER_STORAGE",
  "NONE",
] as const;
export type ResponsibleParty = (typeof RESPONSIBLE_PARTIES)[number];

export const CHECKPOINT_SOURCES = ["SCAN", "MODEL"] as const;
export type CheckpointSource = (typeof CHECKPOINT_SOURCES)[number];

export const ERROR_CODES = [
  "VALIDATION_ERROR",
  "AUTH_REQUIRED",
  "TOKEN_INVALID",
  "TOKEN_EXPIRED",
  "INVALID_CREDENTIALS",
  "FORBIDDEN_ROLE",
  "NOT_OWNER",
  "NOT_FOUND",
  "METHOD_NOT_ALLOWED",
  "PHONE_ALREADY_REGISTERED",
  "BATCH_STATE_INVALID",
  "POOL_STATE_INVALID",
  "POOL_INCOMPATIBLE",
  "LISTING_UNAVAILABLE",
  "SCAN_MISMATCH",
  "INTAKE_NOT_VERIFIED",
  "INTAKE_ALREADY_VERIFIED",
  "DISPUTE_ALREADY_EXISTS",
  "TELEMETRY_OUT_OF_ORDER",
  "AUDIO_TOO_LARGE",
  "AUDIO_FORMAT_UNSUPPORTED",
  "IMPACTS_NOT_DETECTED",
  "SCAN_REJECTED_TAP_VARIATION",
  "WEATHER_UNAVAILABLE",
  "INTERNAL_ERROR",
] as const;
export type ErrorCode = (typeof ERROR_CODES)[number];
/** Frontend-only codes, never sent by the backend. */
export type ClientErrorCode = ErrorCode | "NETWORK_ERROR" | "INVALID_RESPONSE";

// ───────────────────────── Envelopes ─────────────────────────
export interface ApiSuccess<T> {
  success: true;
  data: T;
}
export interface Paginated<T> {
  items: T[];
  nextCursor: string | null;
}
export interface ValidationFieldError {
  /** Dotted camelCase path, e.g. "pickupLatitude" or "rulCurve.0.rulHours" */
  field: string;
  message: string;
  type: string;
}
export interface ApiErrorBody {
  code: ErrorCode;
  message: string;
  /** VALIDATION_ERROR → { fields: ValidationFieldError[] }; other codes → see Section 3 table */
  details: Record<string, unknown>;
}
export interface ApiErrorResponse {
  success: false;
  error: ApiErrorBody;
}
export type ApiResponse<T> = ApiSuccess<T> | ApiErrorResponse;

// ───────────────────────── Shared value objects ─────────────────────────
export interface LocalizedText {
  en: string;
  hi: string;
  mr: string;
  ta: string;
}
export interface RulCurvePoint {
  /** Cooke stiffness index, Hz^2·g^(2/3) */
  stiffnessIndex: number;
  /** Remaining useful life at referenceTempC, hours */
  rulHours: number;
}
export interface HealthStatus {
  status: "OK";
  version: string;
}

// ───────────────────────── Auth & User ─────────────────────────
export interface User {
  id: UUID;
  name: string;
  phone: string;
  role: Role;
  language: Language;
  theme: Theme;
  organizationName: string | null;
  homeLatitude: number | null;
  homeLongitude: number | null;
  createdAt: IsoDateTime;
}
export interface RegisterRequest {
  /** 2–80 chars */
  name: string;
  /** E.164, regex ^\+[1-9][0-9]{9,14}$ e.g. "+919800000001" */
  phone: string;
  /** 8–72 chars */
  password: string;
  role: RegisterRole;
  language: Language;
  /** 2–120 chars or null */
  organizationName: string | null;
}
export interface LoginRequest {
  phone: string;
  password: string;
}
export interface AuthResponse {
  accessToken: string;
  tokenType: "Bearer";
  expiresAt: IsoDateTime;
  user: User;
}
/** PATCH: omit a key to leave it unchanged. null allowed only where typed "| null". */
export interface UpdateProfileRequest {
  name?: string;
  language?: Language;
  theme?: Theme;
  organizationName?: string | null;
  /** homeLatitude and homeLongitude must be sent together (both numbers or both null) */
  homeLatitude?: number | null;
  homeLongitude?: number | null;
}

// ───────────────────────── Crop profiles ─────────────────────────
export interface CropProfile {
  id: UUID;
  /** UPPER_SNAKE key, regex ^[A-Z][A-Z0-9_]{1,49}$, e.g. "TOMATO" */
  cropName: string;
  displayName: LocalizedText;
  ethyleneClass: EthyleneClass;
  harvestWindowDaysMin: number;
  harvestWindowDaysMax: number;
  heatStressTempC: number;
  typicalFruitMassGMin: number;
  typicalFruitMassGMax: number;
  stiffnessGradeAMin: number;
  stiffnessGradeBMin: number;
  defectF0MaxHz: number;
  defectTauMaxMs: number;
  /** ≥ 2 points, strictly ascending by stiffnessIndex */
  rulCurve: RulCurvePoint[];
  q10: number;
  referenceTempC: number;
  intakeStiffnessTolerancePct: number;
  markdownThresholdHours: number;
  defaultMarkdownPct: number;
  disputeToleranceHours: number;
  calibrationNote: string;
  updatedAt: IsoDateTime;
}
export interface CropProfileUpsertRequest {
  cropName: string;
  displayName: LocalizedText;
  ethyleneClass: EthyleneClass;
  harvestWindowDaysMin: number;
  harvestWindowDaysMax: number;
  heatStressTempC: number;
  typicalFruitMassGMin: number;
  typicalFruitMassGMax: number;
  stiffnessGradeAMin: number;
  stiffnessGradeBMin: number;
  defectF0MaxHz: number;
  defectTauMaxMs: number;
  rulCurve: RulCurvePoint[];
  q10: number;
  referenceTempC: number;
  intakeStiffnessTolerancePct: number;
  markdownThresholdHours: number;
  defaultMarkdownPct: number;
  disputeToleranceHours: number;
  calibrationNote: string;
}

// ───────────────────────── HarvestWindow ─────────────────────────
export interface HarvestAdvisoryRequest {
  cropProfileId: UUID;
  /** integer 0–365 */
  daysSinceFlowering: number;
  /** must be in the future and ≤ 14 days ahead */
  targetPickupDate: IsoDateTime;
  latitude: number;
  longitude: number;
  /** demo toggle: integer 0–47 = force ≥ 90% rain probability from that hour for 4 h; null = real forecast only */
  simulateRainInHours: number | null;
}
export interface HarvestAdvisory {
  id: UUID;
  farmerId: UUID;
  cropProfileId: UUID;
  cropName: string;
  daysSinceFlowering: number;
  targetPickupDate: IsoDateTime;
  latitude: number;
  longitude: number;
  /** daysSinceFlowering / harvestWindowDaysMax, 0–1.5, 2 dp */
  maturityFraction: number;
  hoursToPickup: number;
  /** Weather fields below summarise the next 48 h of the Open-Meteo hourly forecast */
  rainProbMaxPct: number;
  rainExpectedInHours: number | null;
  tempMaxC: number;
  humidityMeanPct: number;
  vpdMaxKpa: number;
  weatherRisk: WeatherRisk;
  simulated: boolean;
  recommendation: Recommendation;
  reasonCode: AdvisoryReasonCode;
  /** 0–1, 2 dp */
  confidence: number;
  /** English only; UI renders localized text from reasonCode */
  explanation: string;
  overrideRecommendation: Recommendation | null;
  overrideReason: string | null;
  overriddenBy: UUID | null;
  overriddenAt: IsoDateTime | null;
  /** overrideRecommendation ?? recommendation */
  effectiveRecommendation: Recommendation;
  createdAt: IsoDateTime;
}
export interface AdvisoryOverrideRequest {
  overrideRecommendation: Recommendation;
  /** 5–500 chars */
  overrideReason: string;
}

// ───────────────────────── Batches & Passport ─────────────────────────
export interface CreateBatchRequest {
  cropProfileId: UUID;
  /** > 0, ≤ 50000 */
  weightKg: number;
  /** > 0, ≤ 20000 */
  avgFruitMassG: number;
  harvestedAt: IsoDateTime;
  pickupLatitude: number;
  pickupLongitude: number;
  harvestAdvisoryId: UUID | null;
}
export interface HarvestBatch {
  id: UUID;
  farmerId: UUID;
  farmerName: string;
  cropProfileId: UUID;
  cropName: string;
  ethyleneClass: EthyleneClass;
  harvestAdvisoryId: UUID | null;
  weightKg: number;
  avgFruitMassG: number;
  harvestedAt: IsoDateTime;
  pickupLatitude: number;
  pickupLongitude: number;
  status: BatchStatus;
  qualityGrade: QualityGrade | null;
  internalDefectFlag: boolean;
  stiffnessIndex: number | null;
  loadingStiffnessIndex: number | null;
  initialRulHours: number | null;
  currentRulHours: number | null;
  rulUpdatedAt: IsoDateTime | null;
  rulAtDispatchHours: number | null;
  poolId: UUID | null;
  /** `${FRONTEND_BASE_URL}/passport/${id}` — encode this string in the QR */
  qrCodeValue: string;
  createdAt: IsoDateTime;
}
export interface AcousticScan {
  id: UUID;
  batchId: UUID;
  stage: ScanStage;
  mode: ScanMode;
  clientScanId: UUID;
  f0Hz: number;
  /** TAP: 3 values (one per tap). CHIRP: 1 value. */
  tapF0ValuesHz: number[];
  /** TAP: coefficient of variation of tapF0ValuesHz in %. CHIRP: null */
  tapVariationPct: number | null;
  spectralCentroidHz: number;
  tauMs: number;
  /** exactly 13 values */
  mfccMean: number[];
  avgFruitMassG: number;
  stiffnessIndex: number;
  estimatedRulHours: number;
  grade: QualityGrade;
  internalDefectFlag: boolean;
  phoneModel: string | null;
  sampleRateHz: number;
  scannedBy: UUID;
  recordedAt: IsoDateTime;
  createdAt: IsoDateTime;
}
/** multipart/form-data fields for POST /assay/sonic-scans (all values are strings on the wire) */
export interface SonicScanFormFields {
  /** WAV file: RIFF PCM 16-bit, mono, 44100 or 48000 Hz, 3–15 s, ≤ 2 MB, filename "scan.wav", type "audio/wav" */
  audio: Blob;
  batchId: UUID;
  stage: ScanStage;
  mode: ScanMode;
  clientScanId: UUID;
  recordedAt: IsoDateTime;
  /** optional: omit the field entirely when unknown (never send "null") */
  phoneModel?: string;
  /** optional: omit to use the batch's avgFruitMassG */
  avgFruitMassG?: string;
}
export interface SonicScanResult {
  scan: AcousticScan;
  batch: HarvestBatch;
}

// ───────────────────────── Pools & Telemetry ─────────────────────────
export interface CreatePoolRequest {
  routeTier: RouteTier;
  originLabel: string;
  originLatitude: number;
  originLongitude: number;
  destinationName: string;
  destinationLatitude: number;
  destinationLongitude: number;
  /** > 0, ≤ 40000 */
  maxCapacityKg: number;
  pickupWindowStart: IsoDateTime;
  pickupWindowEnd: IsoDateTime;
}
export interface TransportPool {
  id: UUID;
  carrierId: UUID;
  carrierName: string;
  routeTier: RouteTier;
  status: PoolStatus;
  originLabel: string;
  originLatitude: number;
  originLongitude: number;
  destinationName: string;
  destinationLatitude: number;
  destinationLongitude: number;
  maxCapacityKg: number;
  bookedCapacityKg: number;
  memberCount: number;
  cohortTargetRulHours: number | null;
  ethyleneClasses: EthyleneClass[];
  pickupWindowStart: IsoDateTime;
  pickupWindowEnd: IsoDateTime;
  dispatchedAt: IsoDateTime | null;
  arrivedAt: IsoDateTime | null;
  createdAt: IsoDateTime;
}
export interface PoolMember {
  id: UUID;
  poolId: UUID;
  batchId: UUID;
  farmerId: UUID;
  farmerName: string;
  cropName: string;
  ethyleneClass: EthyleneClass;
  kgBooked: number;
  currentRulHours: number | null;
  reservedAt: IsoDateTime;
}
export interface TransportPoolDetail extends TransportPool {
  members: PoolMember[];
}
export interface PoolMatchRequest {
  batchId: UUID;
}
export interface PoolMatch {
  pool: TransportPool;
  distanceKm: number;
  /** null when the pool has no members yet */
  rulDeltaHours: number | null;
  remainingCapacityKg: number;
  /** 0–1, higher is better, 3 dp */
  score: number;
}
export interface PoolRejection {
  poolId: UUID;
  reasons: CompatibilityReason[];
}
export interface PoolMatchResult {
  batchId: UUID;
  batchRulHours: number;
  requiredRouteTier: RouteTier;
  matches: PoolMatch[];
  rejected: PoolRejection[];
}
export interface CreateReservationRequest {
  batchId: UUID;
}
export interface CancelReservationResult {
  poolId: UUID;
  batchId: UUID;
  batchStatus: BatchStatus;
}
export interface TelemetryIngestRequest {
  /** -10 to 60 */
  tempC: number;
  latitude: number | null;
  longitude: number | null;
  /** null = server time now. Demo simulator may send future times; must be later than the previous reading. */
  recordedAt: IsoDateTime | null;
}
export interface TelemetryReading {
  id: UUID;
  poolId: UUID;
  tempC: number;
  latitude: number | null;
  longitude: number | null;
  recordedAt: IsoDateTime;
  createdAt: IsoDateTime;
}
export interface BatchRulUpdate {
  batchId: UUID;
  previousRulHours: number;
  decayFactor: number;
  consumedHours: number;
  currentRulHours: number;
}
export interface TelemetryIngestResult {
  reading: TelemetryReading;
  intervalHours: number;
  batchUpdates: BatchRulUpdate[];
  rerouteSuggested: boolean;
  suggestedRouteTier: RouteTier | null;
}

// ───────────────────────── Marketplace & Orders ─────────────────────────
export interface CreateListingRequest {
  batchId: UUID;
  /** > 0 and ≤ batch.weightKg */
  quantityKg: number;
  /** > 0, ≤ 100000 */
  pricePerKgInr: number;
}
export interface Listing {
  id: UUID;
  batchId: UUID;
  farmerId: UUID;
  farmerName: string;
  cropProfileId: UUID;
  cropName: string;
  qualityGrade: QualityGrade;
  internalDefectFlag: boolean;
  quantityKg: number;
  availableKg: number;
  pricePerKgInr: number;
  currentRulHours: number;
  routeTier: RouteTier;
  guaranteedArrivalRulHours: number;
  pickupLatitude: number;
  pickupLongitude: number;
  status: ListingStatus;
  createdAt: IsoDateTime;
}
export interface CreateOrderRequest {
  listingId: UUID;
  /** > 0 and ≤ listing.availableKg */
  quantityKg: number;
}
export interface BuyerOrder {
  id: UUID;
  buyerId: UUID;
  buyerName: string;
  listingId: UUID;
  batchId: UUID;
  cropName: string;
  quantityKg: number;
  pricePerKgInr: number;
  totalPriceInr: number;
  guaranteedArrivalRulHours: number;
  status: OrderStatus;
  intakeScanId: UUID | null;
  intakeResult: IntakeResult | null;
  intakeStiffnessDropPct: number | null;
  rulAtIntakeHours: number | null;
  storageTempC: number | null;
  intakeVerifiedAt: IsoDateTime | null;
  markdownPct: number;
  markdownTriggeredAt: IsoDateTime | null;
  createdAt: IsoDateTime;
}

// ───────────────────────── Dark-store intake & markdown ─────────────────────────
export interface IntakeVerifyRequest {
  orderId: UUID;
  scanId: UUID;
  /** -5 to 45 */
  storageTempC: number;
}
export interface IntakeVerifyResult {
  order: BuyerOrder;
  referenceStiffnessIndex: number;
  intakeStiffnessIndex: number;
  stiffnessDropPct: number;
  tolerancePct: number;
  result: IntakeResult;
}
export interface MarkdownCheckRequest {
  /** demo fast-forward: 0–240 hours, or null for "now" */
  simulateHoursAhead: number | null;
}
export interface MarkdownWebhookPayload {
  event: "FLASH_MARKDOWN";
  orderId: UUID;
  batchId: UUID;
  cropName: string;
  markdownPct: number;
  shelfRulHours: number;
  triggeredAt: IsoDateTime;
}
export interface MarkdownCheckResult {
  order: BuyerOrder;
  shelfRulHours: number;
  thresholdHours: number;
  markdownActive: boolean;
  newlyTriggered: boolean;
  /** non-null only when newlyTriggered is true */
  webhookPayload: MarkdownWebhookPayload | null;
}

// ───────────────────────── Disputes ─────────────────────────
export interface CreateDisputeRequest {
  orderId: UUID;
  /** 10–1000 chars */
  description: string;
}
export interface DisputeSegment {
  /** never "NONE" */
  party: ResponsibleParty;
  startAt: IsoDateTime;
  endAt: IsoDateTime;
  elapsedHours: number;
  actualLossHours: number;
  expectedLossHours: number;
  excessLossHours: number;
}
export interface DisputeReport {
  id: UUID;
  orderId: UUID;
  batchId: UUID;
  raisedBy: UUID;
  raisedByRole: Role;
  description: string;
  rulFarmGateHours: number;
  rulLoadingHours: number;
  rulIntakeHours: number;
  rulShelfHours: number;
  farmGateAt: IsoDateTime;
  loadingAt: IsoDateTime;
  intakeAt: IsoDateTime;
  assessedAt: IsoDateTime;
  loadingCheckpointSource: CheckpointSource;
  /** always 3 items in order FARM, TRANSIT, BUYER_STORAGE */
  segments: DisputeSegment[];
  responsibleParty: ResponsibleParty;
  createdAt: IsoDateTime;
}

// ───────────────────────── Batch passport (public) ─────────────────────────
export interface BatchPassport {
  batch: HarvestBatch;
  /** all scans for the batch, ascending by recordedAt */
  scans: AcousticScan[];
  pool: TransportPool | null;
  /** pool telemetry, ascending by recordedAt; [] if not pooled */
  telemetry: TelemetryReading[];
}

// ───────────────────────── Route map (single source for the API client) ─────────────────────────
// Key = "METHOD /path" relative to /api/v1. ":param" = path param. query = query-string params.
// body "multipart" = FormData built from SonicScanFormFields. body null = send no body.
export interface ApiRoutes {
  "GET /health": { query: null; body: null; res: HealthStatus };
  "POST /auth/register": {
    query: null;
    body: RegisterRequest;
    res: AuthResponse;
  };
  "POST /auth/login": { query: null; body: LoginRequest; res: AuthResponse };
  "GET /users/me": { query: null; body: null; res: User };
  "PATCH /users/me": { query: null; body: UpdateProfileRequest; res: User };
  "GET /crop-profiles": {
    query: { limit?: number; cursor?: string };
    body: null;
    res: Paginated<CropProfile>;
  };
  "GET /crop-profiles/:cropProfileId": {
    query: null;
    body: null;
    res: CropProfile;
  };
  "POST /crop-profiles": {
    query: null;
    body: CropProfileUpsertRequest;
    res: CropProfile;
  };
  "PUT /crop-profiles/:cropProfileId": {
    query: null;
    body: CropProfileUpsertRequest;
    res: CropProfile;
  };
  "POST /harvest-advisories": {
    query: null;
    body: HarvestAdvisoryRequest;
    res: HarvestAdvisory;
  };
  "GET /harvest-advisories": {
    query: { limit?: number; cursor?: string };
    body: null;
    res: Paginated<HarvestAdvisory>;
  };
  "GET /harvest-advisories/:advisoryId": {
    query: null;
    body: null;
    res: HarvestAdvisory;
  };
  "POST /harvest-advisories/:advisoryId/override": {
    query: null;
    body: AdvisoryOverrideRequest;
    res: HarvestAdvisory;
  };
  "POST /batches": { query: null; body: CreateBatchRequest; res: HarvestBatch };
  "GET /batches": {
    query: { status?: BatchStatus; limit?: number; cursor?: string };
    body: null;
    res: Paginated<HarvestBatch>;
  };
  "GET /batches/:batchId": { query: null; body: null; res: HarvestBatch };
  "GET /passport/:batchId": { query: null; body: null; res: BatchPassport };
  "POST /assay/sonic-scans": {
    query: null;
    body: "multipart";
    res: SonicScanResult;
  };
  "GET /pools": {
    query: {
      status?: PoolStatus;
      routeTier?: RouteTier;
      mine?: boolean;
      limit?: number;
      cursor?: string;
    };
    body: null;
    res: Paginated<TransportPool>;
  };
  "POST /pools": {
    query: null;
    body: CreatePoolRequest;
    res: TransportPoolDetail;
  };
  "GET /pools/:poolId": { query: null; body: null; res: TransportPoolDetail };
  "POST /pools/match": {
    query: null;
    body: PoolMatchRequest;
    res: PoolMatchResult;
  };
  "POST /pools/:poolId/reservations": {
    query: null;
    body: CreateReservationRequest;
    res: PoolMember;
  };
  "DELETE /pools/:poolId/reservations/:batchId": {
    query: null;
    body: null;
    res: CancelReservationResult;
  };
  "POST /pools/:poolId/dispatch": {
    query: null;
    body: null;
    res: TransportPoolDetail;
  };
  "POST /pools/:poolId/telemetry": {
    query: null;
    body: TelemetryIngestRequest;
    res: TelemetryIngestResult;
  };
  "GET /pools/:poolId/telemetry": {
    query: { limit?: number; cursor?: string };
    body: null;
    res: Paginated<TelemetryReading>;
  };
  "POST /pools/:poolId/arrive": {
    query: null;
    body: null;
    res: TransportPoolDetail;
  };
  "GET /listings": {
    query: {
      cropProfileId?: UUID;
      grade?: QualityGrade;
      minArrivalRulHours?: number;
      mine?: boolean;
      limit?: number;
      cursor?: string;
    };
    body: null;
    res: Paginated<Listing>;
  };
  "POST /listings": { query: null; body: CreateListingRequest; res: Listing };
  "GET /listings/:listingId": { query: null; body: null; res: Listing };
  "POST /listings/:listingId/withdraw": {
    query: null;
    body: null;
    res: Listing;
  };
  "POST /orders": { query: null; body: CreateOrderRequest; res: BuyerOrder };
  "GET /orders": {
    query: { status?: OrderStatus; limit?: number; cursor?: string };
    body: null;
    res: Paginated<BuyerOrder>;
  };
  "GET /orders/:orderId": { query: null; body: null; res: BuyerOrder };
  "POST /intake/verify": {
    query: null;
    body: IntakeVerifyRequest;
    res: IntakeVerifyResult;
  };
  "POST /orders/:orderId/markdown-check": {
    query: null;
    body: MarkdownCheckRequest;
    res: MarkdownCheckResult;
  };
  "POST /disputes": {
    query: null;
    body: CreateDisputeRequest;
    res: DisputeReport;
  };
  "GET /disputes": {
    query: { limit?: number; cursor?: string };
    body: null;
    res: Paginated<DisputeReport>;
  };
  "GET /disputes/:disputeId": { query: null; body: null; res: DisputeReport };
}
export type ApiRouteKey = keyof ApiRoutes;
