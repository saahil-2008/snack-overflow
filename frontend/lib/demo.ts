import type {
  HarvestBatch,
  TransportPool,
  Listing,
  User,
  BuyerOrder,
} from "./api/types";
export const DEMO_USER: User = {
  id: "10000000-0000-4000-8000-000000000001",
  name: "Ramesh Pawar",
  phone: "+919800000001",
  role: "FARMER",
  language: "EN",
  theme: "LIGHT",
  organizationName: "Pimpalgaon Tomato FPO",
  homeLatitude: 20.1667,
  homeLongitude: 73.9833,
  createdAt: "2026-10-24T06:00:00Z",
};
export const id = (n: number) =>
  `20000000-0000-4000-8000-${String(n).padStart(12, "0")}`;
export const DEMO_BATCHES: HarvestBatch[] = [
  "TOMATO",
  "MANGO",
  "POMEGRANATE",
  "CUCUMBER",
].map((cropName, i) => ({
  id: id(i + 1),
  farmerId: DEMO_USER.id,
  farmerName: DEMO_USER.name,
  cropProfileId: id(i + 21),
  cropName,
  ethyleneClass: i === 0 ? "EMITTER" : "NEUTRAL",
  harvestAdvisoryId: null,
  weightKg: [320, 180, 250, 140][i],
  avgFruitMassG: [120, 240, 200, 180][i],
  harvestedAt: "2026-10-24T06:00:00Z",
  pickupLatitude: 20.1667,
  pickupLongitude: 73.9833,
  status: i === 3 ? "PENDING_ASSAY" : i === 0 ? "POOLED" : "GRADED",
  qualityGrade: i === 3 ? null : i === 2 ? "B" : "A",
  internalDefectFlag: false,
  stiffnessIndex: i === 3 ? null : 3200000,
  loadingStiffnessIndex: null,
  initialRulHours: i === 3 ? null : [72, 96, 120][i],
  currentRulHours: i === 3 ? null : [68, 92, 116][i],
  rulUpdatedAt: null,
  rulAtDispatchHours: null,
  poolId: i === 0 ? id(41) : null,
  qrCodeValue: `/passport/${id(i + 1)}`,
  createdAt: "2026-10-24T06:00:00Z",
}));
export const DEMO_POOLS: TransportPool[] = [
  "Nashik Road Dark Store",
  "Vashi APMC, Navi Mumbai",
  "Pune Fresh Market",
].map((destinationName, i) => ({
  id: id(i + 41),
  carrierId: id(50),
  carrierName: [
    "Sahyadri Reefer Lines",
    "GreenRoute Logistics",
    "FreshWay Transport",
  ][i],
  routeTier:
    i === 0 ? "FAST_QCOMM" : i === 1 ? "FLEX_REGIONAL" : "STANDARD_WHOLESALE",
  status: "OPEN",
  originLabel: "Pimpalgaon, Nashik",
  originLatitude: 20.1667,
  originLongitude: 73.9833,
  destinationName,
  destinationLatitude: 19.95,
  destinationLongitude: 73.83,
  maxCapacityKg: [2000, 4000, 3000][i],
  bookedCapacityKg: [1480, 2360, 1100][i],
  memberCount: [6, 8, 4][i],
  cohortTargetRulHours: 72,
  ethyleneClasses: ["EMITTER"],
  pickupWindowStart: "2026-10-25T07:00:00Z",
  pickupWindowEnd: "2026-10-25T10:00:00Z",
  dispatchedAt: null,
  arrivedAt: null,
  createdAt: "2026-10-24T06:00:00Z",
}));
export const DEMO_LISTINGS: Listing[] = DEMO_BATCHES.slice(0, 3).map(
  (b, i) => ({
    id: id(i + 61),
    batchId: b.id,
    farmerId: b.farmerId,
    farmerName: b.farmerName,
    cropProfileId: b.cropProfileId,
    cropName: b.cropName,
    qualityGrade: b.qualityGrade || "A",
    internalDefectFlag: false,
    quantityKg: b.weightKg,
    availableKg: b.weightKg,
    pricePerKgInr: [32, 85, 110][i],
    currentRulHours: b.currentRulHours || 72,
    routeTier: "FAST_QCOMM",
    guaranteedArrivalRulHours: 60,
    pickupLatitude: 20.1667,
    pickupLongitude: 73.9833,
    status: "ACTIVE",
    createdAt: "2026-10-24T06:00:00Z",
  }),
);
export const DEMO_ORDERS: BuyerOrder[] = [];
export const cropName = (s: string) => s.charAt(0) + s.slice(1).toLowerCase();
export const produce = (s: string) =>
  ({
    TOMATO: "🍅",
    MANGO: "🥭",
    POMEGRANATE: "🍎",
    CUCUMBER: "🥒",
    WATERMELON: "🍉",
  })[s] || "🌱";
export const money = (n: number) =>
  new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(n);
