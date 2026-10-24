"use client";
import { useState, useEffect, useRef, useCallback } from "react";
import { usePathname, useRouter } from "next/navigation";
import { QRCodeSVG } from "qrcode.react";
import {
  Sprout,
  LayoutDashboard,
  ScanLine,
  Package,
  Truck,
  ShoppingBasket,
  ClipboardList,
  Settings,
  ArrowUpRight,
  ArrowRight,
  ChevronRight,
  MapPin,
  Sun,
  Bell,
  Leaf,
  Plus,
  Search,
  X,
  Check,
  CircleCheck,
  Clock3,
  ShieldCheck,
  TrendingUp,
  CloudSun,
  Droplets,
  Wind,
  Volume2,
  Mic,
  Upload,
  LogOut,
  Menu,
  Moon,
  Radio,
  QrCode,
  Loader2,
  AlertTriangle,
  Users,
  Globe,
  CalendarDays,
  SlidersHorizontal,
  RefreshCw,
  Download,
} from "lucide-react";
import {
  api,
  tokenStore,
  ApiError,
  buildSonicScanForm,
  encodeWav,
} from "@/lib/api/client";
import type {
  HarvestBatch,
  TransportPool,
  Listing,
  BuyerOrder,
  User,
  CropProfile,
  HarvestAdvisory,
  BatchPassport,
  Role,
  Language,
  Theme,
  PoolMatch,
} from "@/lib/api/types";
import {
  DEMO_BATCHES,
  DEMO_POOLS,
  DEMO_LISTINGS,
  DEMO_USER,
  cropName,
  produce,
  money,
  id,
} from "@/lib/demo";

type View =
  | "home"
  | "harvest"
  | "scan"
  | "batches"
  | "pools"
  | "market"
  | "orders"
  | "settings"
  | "passport"
  | "admin";
const links = [
  { view: "home", label: "Overview", icon: LayoutDashboard, path: "/farmer" },
  {
    view: "harvest",
    label: "Harvest window",
    icon: CloudSun,
    path: "/farmer/harvest-window",
  },
  {
    view: "scan",
    label: "Quality scan",
    icon: ScanLine,
    path: "/farmer/quality-scan",
  },
  {
    view: "batches",
    label: "My harvest",
    icon: Package,
    path: "/farmer/batches",
  },
  { view: "pools", label: "Shared transport", icon: Truck, path: "/logistics" },
  {
    view: "market",
    label: "Marketplace",
    icon: ShoppingBasket,
    path: "/buyer/marketplace",
  },
  {
    view: "orders",
    label: "Orders",
    icon: ClipboardList,
    path: "/farmer/orders",
  },
] as const;
const words: Record<Language, Record<string, string>> = {
  EN: {
    home: "Overview",
    harvest: "Harvest window",
    scan: "Quality scan",
    batches: "My harvest",
    pools: "Shared transport",
    market: "Marketplace",
    orders: "Orders",
    hello: "Good morning",
    tagline: "Healthy produce. Stronger together.",
  },
  HI: {
    home: "अवलोकन",
    harvest: "कटाई का समय",
    scan: "गुणवत्ता जाँच",
    batches: "मेरी फसल",
    pools: "साझा परिवहन",
    market: "बाज़ार",
    orders: "ऑर्डर",
    hello: "सुप्रभात",
    tagline: "स्वस्थ उपज। साथ में मज़बूत।",
  },
  MR: {
    home: "आढावा",
    harvest: "कापणीची वेळ",
    scan: "गुणवत्ता तपासणी",
    batches: "माझे पीक",
    pools: "सामायिक वाहतूक",
    market: "बाजारपेठ",
    orders: "ऑर्डर",
    hello: "सुप्रभात",
    tagline: "निरोगी उत्पादन. एकत्र मजबूत.",
  },
  TA: {
    home: "கண்ணோட்டம்",
    harvest: "அறுவடை நேரம்",
    scan: "தரச் சோதனை",
    batches: "என் அறுவடை",
    pools: "பகிர்வு போக்குவரத்து",
    market: "சந்தை",
    orders: "ஆர்டர்கள்",
    hello: "காலை வணக்கம்",
    tagline: "ஆரோக்கியமான விளைபொருட்கள். ஒன்றாக வலுவாக.",
  },
};
const viewFor = (p: string): View =>
  p.includes("passport")
    ? "passport"
    : p.includes("settings")
      ? "settings"
      : p.includes("crop-profiles")
        ? "admin"
        : p.includes("harvest-window")
          ? "harvest"
          : p.includes("quality-scan")
            ? "scan"
            : p.includes("batches")
              ? "batches"
              : p.includes("logistics")
                ? "pools"
                : p.includes("marketplace") || p.includes("listings")
                  ? "market"
                  : p.includes("orders")
                    ? "orders"
                    : "home";
const saved = <T,>(key: string, fallback: T): T => {
  try {
    return JSON.parse(localStorage.getItem(key) || "null") ?? fallback;
  } catch {
    return fallback;
  }
};
export default function FarmApp() {
  const router = useRouter(),
    path = usePathname();
  const view = viewFor(path);
  const [demo, setDemo] = useState(true),
    [ready, setReady] = useState(false),
    [user, setUser] = useState<User>(DEMO_USER),
    [language, setLanguage] = useState<Language>("EN"),
    [theme, setTheme] = useState<Theme>("LIGHT");
  const [batches, setBatches] = useState<HarvestBatch[]>(DEMO_BATCHES),
    [pools, setPools] = useState<TransportPool[]>(DEMO_POOLS),
    [listings, setListings] = useState<Listing[]>(DEMO_LISTINGS),
    [orders, setOrders] = useState<BuyerOrder[]>([]),
    [crops, setCrops] = useState<CropProfile[]>([]),
    [advisory, setAdvisory] = useState<HarvestAdvisory | null>(null),
    [passport, setPassport] = useState<BatchPassport | null>(null);
  const [toast, setToast] = useState(""),
    [busy, setBusy] = useState(false),
    [online, setOnline] = useState(false),
    [sidebar, setSidebar] = useState(false),
    [notifications, setNotifications] = useState(false),
    [modal, setModal] = useState<
      "batch" | "login" | "register" | "listing" | "order" | "pool" | null
    >(null),
    [selected, setSelected] = useState<HarvestBatch>(DEMO_BATCHES[0]),
    [selectedListing, setSelectedListing] = useState<Listing>(DEMO_LISTINGS[0]),
    [filter, setFilter] = useState("All batches"),
    [search, setSearch] = useState(""),
    [scanState, setScanState] = useState<
      "idle" | "recording" | "processing" | "done"
    >("idle"),
    [scanStep, setScanStep] = useState(""),
    [rain, setRain] = useState(false),
    [demoAdvice, setDemoAdvice] = useState(false),
    [matches, setMatches] = useState<PoolMatch[] | null>(null);
  const recording = useRef(false),
    canvas = useRef<HTMLCanvasElement>(null);
  const t = words[language];
  const notify = (s: string) => setToast(s);
  const run = async (action: () => Promise<void>) => {
    setBusy(true);
    try {
      await action();
    } catch (e) {
      notify(
        e instanceof Error
          ? e.message
          : "Something went wrong. Please try again.",
      );
      if (e instanceof ApiError && e.status === 401) setModal("login");
    } finally {
      setBusy(false);
    }
  };
  useEffect(() => {
    setDemo(saved("fp_demo", true));
    setUser(saved("fp_demo_user", DEMO_USER));
    setPools(saved("fp_demo_pools", DEMO_POOLS));
    setLanguage(saved("fp_language", "EN"));
    setTheme(saved("fp_theme", "LIGHT"));
    setBatches(saved("fp_demo_batches", DEMO_BATCHES));
    setOrders(saved("fp_demo_orders", []));
    setListings(saved("fp_demo_listings", DEMO_LISTINGS));
    setReady(true);
    api("GET /health")
      .then(() => setOnline(true))
      .catch(() => setOnline(false));
  }, []);
  useEffect(() => {
    if (ready) {
      localStorage.setItem("fp_demo", JSON.stringify(demo));
      localStorage.setItem("fp_language", JSON.stringify(language));
      localStorage.setItem("fp_theme", JSON.stringify(theme));
      if (demo) {
        localStorage.setItem("fp_demo_user", JSON.stringify(user));
        localStorage.setItem("fp_demo_pools", JSON.stringify(pools));
        localStorage.setItem("fp_demo_batches", JSON.stringify(batches));
        localStorage.setItem("fp_demo_orders", JSON.stringify(orders));
        localStorage.setItem("fp_demo_listings", JSON.stringify(listings));
      }
    }
  }, [ready, demo, batches, orders, listings, language, theme, user, pools]);
  useEffect(() => {
    document.documentElement.dataset.theme =
      theme === "SYSTEM"
        ? matchMedia("(prefers-color-scheme: dark)").matches
          ? "DARK"
          : "LIGHT"
        : theme;
    document.documentElement.lang = { EN: "en", HI: "hi", MR: "mr", TA: "ta" }[
      language
    ];
  }, [theme, language]);
  useEffect(() => {
    if (toast) {
      const h = setTimeout(() => setToast(""), 5000);
      return () => clearTimeout(h);
    }
  }, [toast]);
  useEffect(
    () => () => {
      recording.current = false;
    },
    [],
  );
  const load = useCallback(async () => {
    if (demo) return;
    const me = await api("GET /users/me");
    setUser(me);
    setLanguage(me.language);
    const results = await Promise.allSettled([
      api("GET /batches"),
      api("GET /pools"),
      api("GET /listings"),
      api("GET /orders"),
      api("GET /crop-profiles"),
    ]);
    if (results[0].status === "fulfilled") setBatches(results[0].value.items);
    if (results[1].status === "fulfilled") setPools(results[1].value.items);
    if (results[2].status === "fulfilled") setListings(results[2].value.items);
    if (results[3].status === "fulfilled") setOrders(results[3].value.items);
    if (results[4].status === "fulfilled") setCrops(results[4].value.items);
    const failed = results.find((r) => r.status === "rejected");
    if (failed?.status === "rejected") throw failed.reason;
  }, [demo]);
  useEffect(() => {
    if (ready && !demo && tokenStore.get()) run(load);
  }, [ready, demo, load]);
  useEffect(() => {
    if (view === "passport") {
      const batchId = path.split("/").pop() || selected.id;
      if (demo && batches.some((b) => b.id === batchId)) {
        const b = batches.find((b) => b.id === batchId) || selected;
        setPassport({
          batch: b,
          scans: [],
          pool: pools.find((p) => p.id === b.poolId) || null,
          telemetry: [],
        });
      } else
        run(async () =>
          setPassport(
            await api("GET /passport/:batchId", { params: { batchId } }),
          ),
        );
    }
  }, [path, demo, view]);
  useEffect(() => {
    if (path === "/login") setModal("login");
    if (path === "/register") setModal("register");
    if (path === "/farmer/batches/new") setModal("batch");
  }, [path]);
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setModal(null);
        setSidebar(false);
        setNotifications(false);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);
  const go = (v: View) => {
    setSidebar(false);
    setSearch("");
    router.push(
      v === "settings"
        ? "/settings"
        : v === "admin"
          ? "/admin/crop-profiles"
          : links.find((l) => l.view === v)?.path || "/farmer",
    );
  };
  const changeRole = (role: Role) => {
    if (!demo) {
      notify("Sign in with the account for this role.");
      setModal("login");
      return;
    }
    setUser({
      ...DEMO_USER,
      role,
      name:
        role === "BUYER"
          ? "Arjun Mehta"
          : role === "LOGISTICS"
            ? "Sunita Logistics"
            : role === "ADMIN"
              ? "Dr. Kavita Rao"
              : DEMO_USER.name,
    });
    go(
      role === "BUYER"
        ? "market"
        : role === "LOGISTICS"
          ? "pools"
          : role === "ADMIN"
            ? "admin"
            : "home",
    );
  };
  const visibleBatches = batches.filter(
    (b) =>
      (filter === "All batches" ||
        (filter === "Needs a scan"
          ? b.status === "PENDING_ASSAY"
          : filter === "Graded"
            ? b.status === "GRADED"
            : b.poolId !== null)) &&
      `${b.cropName} ${b.id}`.toLowerCase().includes(search.toLowerCase()),
  );
  const totalKg = batches.reduce((a, b) => a + b.weightKg, 0),
    pending = batches.filter((b) => b.status === "PENDING_ASSAY").length;
  const openScan = (batch?: HarvestBatch) => {
    if (batch) setSelected(batch);
    setScanState("idle");
    go("scan");
  };
  const batchDetails = (b: HarvestBatch) => {
    setSelected(b);
    router.push(`/passport/${b.id}`);
  };
  async function record() {
    if (!batches.length) {
      notify("Create a harvest batch first.");
      return;
    }
    setScanState("recording");
    setScanStep("Stay quiet · preparing your scan");
    if (demo) {
      for (const [i, s] of [
        "Stay quiet · calibrating background noise",
        "Tap 1 · gently tap the fruit",
        "Tap 2 · same spot, same pressure",
        "Tap 3 · one last tap",
        "Analysing acoustic signature…",
      ].entries()) {
        await new Promise((r) => setTimeout(r, 1000));
        setScanStep(s);
        if (i === 4) setScanState("processing");
      }
      setBatches((bs) =>
        bs.map((b) =>
          b.id === selected.id
            ? {
                ...b,
                status: "GRADED",
                qualityGrade: "A",
                currentRulHours: 72,
                initialRulHours: 72,
                stiffnessIndex: 3200000,
              }
            : b,
        ),
      );
      setScanState("done");
      return;
    }
    let stream: MediaStream | null = null,
      context: AudioContext | null = null;
    try {
      stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: false,
          noiseSuppression: false,
          autoGainControl: false,
          channelCount: 1,
        },
      });
      context = new AudioContext({ sampleRate: 44100 });
      if (context.sampleRate !== 44100 && context.sampleRate !== 48000)
        throw new Error(
          "Unsupported device audio rate. Please upload a 44.1 or 48 kHz WAV file.",
        );
      const chunks: Float32Array[] = [];
      const source = context.createMediaStreamSource(stream);
      const recorder = context.createScriptProcessor(4096, 1, 1);
      const analyser = context.createAnalyser();
      analyser.fftSize = 2048;
      source.connect(analyser);
      source.connect(recorder);
      recorder.connect(context.destination);
      recorder.onaudioprocess = (e) =>
        chunks.push(new Float32Array(e.inputBuffer.getChannelData(0)));
      recording.current = true;
      const draw = () => {
        if (!recording.current) return;
        const c = canvas.current,
          ctx = c?.getContext("2d");
        if (c && ctx) {
          const values = new Uint8Array(analyser.frequencyBinCount);
          analyser.getByteFrequencyData(values);
          ctx.clearRect(0, 0, c.width, c.height);
          ctx.fillStyle = "#2b8251";
          for (let i = 0; i < 60; i++) {
            const h = (values[i * 4] / 255) * c.height;
            ctx.fillRect((i * c.width) / 60, c.height - h, c.width / 80, h);
          }
        }
        requestAnimationFrame(draw);
      };
      draw();
      for (let n = 0; n < 8; n++) {
        setScanStep(
          n < 2
            ? "Stay quiet · calibrating"
            : n < 4
              ? "Tap 1 · gently tap the fruit"
              : n < 6
                ? "Tap 2 · same spot"
                : "Tap 3 · one last tap",
        );
        await new Promise((r) => setTimeout(r, 1000));
      }
      recording.current = false;
      recorder.disconnect();
      source.disconnect();
      const size = chunks.reduce((n, a) => n + a.length, 0),
        samples = new Float32Array(size);
      let offset = 0;
      for (const c of chunks) {
        samples.set(c, offset);
        offset += c.length;
      }
      setScanState("processing");
      await submitWav(encodeWav(samples, context.sampleRate));
    } catch (e) {
      setScanState("idle");
      notify(
        e instanceof Error
          ? e.message
          : "Microphone access is unavailable. Try WAV upload.",
      );
    } finally {
      recording.current = false;
      stream?.getTracks().forEach((t) => t.stop());
      await context?.close();
    }
  }
  async function submitWav(wav: Blob) {
    const result = await api("POST /assay/sonic-scans", {
      body: buildSonicScanForm({
        wav,
        batchId: selected.id,
        stage:
          user.role === "LOGISTICS"
            ? "LOADING"
            : user.role === "BUYER"
              ? "INTAKE"
              : "FARM_GATE",
        mode: "TAP",
        clientScanId: crypto.randomUUID(),
        recordedAt: new Date().toISOString().replace(/\.\d{3}Z$/, "Z"),
        phoneModel: null,
        avgFruitMassG: selected.avgFruitMassG,
      }),
    });
    setSelected(result.batch);
    setBatches((bs) =>
      bs.map((b) => (b.id === result.batch.id ? result.batch : b)),
    );
    setScanState("done");
  }
  async function reserve(p: TransportPool) {
    await run(async () => {
      if (demo) {
        if (selected.status === "PENDING_ASSAY")
          throw new Error("Scan this batch before booking transport.");
        setBatches((bs) =>
          bs.map((b) =>
            b.id === selected.id ? { ...b, status: "POOLED", poolId: p.id } : b,
          ),
        );
        setPools((ps) =>
          ps.map((x) =>
            x.id === p.id
              ? {
                  ...x,
                  bookedCapacityKg: x.bookedCapacityKg + selected.weightKg,
                  memberCount: x.memberCount + 1,
                }
              : x,
          ),
        );
      } else {
        await api("POST /pools/:poolId/reservations", {
          params: { poolId: p.id },
          body: { batchId: selected.id },
        });
        await load();
      }
      notify("Your space is reserved. Growing together, going together.");
    });
  }
  async function submitForm(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const f = new FormData(e.currentTarget),
      val = (k: string) => String(f.get(k) || "");
    await run(async () => {
      if (modal === "login" || modal === "register") {
        const auth =
          modal === "login"
            ? await api("POST /auth/login", {
                body: { phone: val("phone"), password: val("password") },
              })
            : await api("POST /auth/register", {
                body: {
                  name: val("name"),
                  phone: val("phone"),
                  password: val("password"),
                  role: val("role") as "FARMER" | "BUYER" | "LOGISTICS",
                  language,
                  organizationName: val("organization") || null,
                },
              });
        tokenStore.set(auth.accessToken);
        const me = await api("GET /users/me");
        setUser(me);
        setBatches([]);
        setListings([]);
        setOrders([]);
        setDemo(false);
        go(
          me.role === "BUYER"
            ? "market"
            : me.role === "LOGISTICS"
              ? "pools"
              : me.role === "ADMIN"
                ? "admin"
                : "home",
        );
        notify("Connected to your farm. Welcome back.");
      }
      if (modal === "batch") {
        const crop = val("crop");
        const body = {
          cropProfileId: crop,
          weightKg: Number(val("weight")),
          avgFruitMassG: Number(val("mass")),
          harvestedAt: new Date(val("date")).toISOString(),
          pickupLatitude: Number(val("latitude")),
          pickupLongitude: Number(val("longitude")),
          harvestAdvisoryId: null,
        };
        const batch = demo
          ? {
              ...DEMO_BATCHES[3],
              ...body,
              id: crypto.randomUUID(),
              cropName: crop,
              status: "PENDING_ASSAY" as const,
              createdAt: new Date().toISOString(),
            }
          : await api("POST /batches", { body });
        setBatches((bs) => [batch, ...bs]);
        setSelected(batch);
        go("batches");
        notify("Harvest batch added. Next up: a quick quality scan.");
      }
      if (modal === "listing") {
        const body = {
          batchId: selected.id,
          quantityKg: Number(val("quantity")),
          pricePerKgInr: Number(val("price")),
        };
        const listing = demo
          ? {
              ...DEMO_LISTINGS[0],
              ...body,
              id: crypto.randomUUID(),
              cropName: selected.cropName,
              availableKg: body.quantityKg,
              qualityGrade: selected.qualityGrade || "A",
              currentRulHours: selected.currentRulHours || 72,
            }
          : await api("POST /listings", { body });
        setListings((ls) => [listing, ...ls]);
        notify("Your produce is now on the marketplace.");
      }
      if (modal === "order") {
        const quantityKg = Number(val("quantity"));
        if (quantityKg > selectedListing.availableKg)
          throw new Error("Requested quantity exceeds available stock.");
        const order = demo
          ? {
              id: crypto.randomUUID(),
              buyerId: user.id,
              buyerName: user.name,
              listingId: selectedListing.id,
              batchId: selectedListing.batchId,
              cropName: selectedListing.cropName,
              quantityKg,
              pricePerKgInr: selectedListing.pricePerKgInr,
              totalPriceInr: quantityKg * selectedListing.pricePerKgInr,
              guaranteedArrivalRulHours:
                selectedListing.guaranteedArrivalRulHours,
              status: "PLACED" as const,
              intakeScanId: null,
              intakeResult: null,
              intakeStiffnessDropPct: null,
              rulAtIntakeHours: null,
              storageTempC: null,
              intakeVerifiedAt: null,
              markdownPct: 0,
              markdownTriggeredAt: null,
              createdAt: new Date().toISOString(),
            }
          : await api("POST /orders", {
              body: { listingId: selectedListing.id, quantityKg },
            });
        setOrders((os) => [order, ...os]);
        setListings((ls) =>
          ls.map((l) =>
            l.id === selectedListing.id
              ? { ...l, availableKg: l.availableKg - quantityKg }
              : l,
          ),
        );
        notify("Order placed. Freshness, reserved.");
      }
      if (modal === "pool") {
        const body = {
          routeTier: "FAST_QCOMM" as const,
          originLabel: val("origin"),
          originLatitude: 20.1667,
          originLongitude: 73.9833,
          destinationName: val("destination"),
          destinationLatitude: 19.9548,
          destinationLongitude: 73.837,
          maxCapacityKg: Number(val("capacity")),
          pickupWindowStart: new Date(val("start")).toISOString(),
          pickupWindowEnd: new Date(val("end")).toISOString(),
        };
        const pool = demo
          ? {
              ...DEMO_POOLS[0],
              ...body,
              id: crypto.randomUUID(),
              bookedCapacityKg: 0,
              memberCount: 0,
            }
          : await api("POST /pools", { body });
        setPools((ps) => [pool, ...ps]);
        notify("New transport pool created.");
      }
      setModal(null);
    });
  }
  const batchTable = (compact = false) => (
    <div className="table-scroll">
      <table>
        <thead>
          <tr>
            <th>Produce / batch</th>
            <th>Quantity</th>
            <th>Quality</th>
            <th>Freshness left</th>
            <th>Status</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {(compact ? batches.slice(0, 3) : visibleBatches).map((b, i) => (
            <tr key={b.id}>
              <td>
                <div className="produce-cell">
                  <span
                    className={`produce-thumb crop-${b.cropName.toLowerCase()}`}
                  >
                    {produce(b.cropName)}
                  </span>
                  <div>
                    <strong>{cropName(b.cropName)}</strong>
                    <small>
                      FP–{String(i + 241).padStart(4, "0")} · Nashik
                    </small>
                  </div>
                </div>
              </td>
              <td>
                <strong>{b.weightKg}</strong> <span className="muted">kg</span>
              </td>
              <td>
                {b.qualityGrade ? (
                  <span className="grade">
                    <ShieldCheck size={14} /> Grade {b.qualityGrade}
                  </span>
                ) : (
                  <span className="muted">Not scanned</span>
                )}
              </td>
              <td>
                {b.currentRulHours ? (
                  <div className="freshness">
                    <span>
                      {b.currentRulHours} <small>hours</small>
                    </span>
                    <i>
                      <b
                        style={{
                          width: `${Math.min(100, b.currentRulHours / 1.2)}%`,
                        }}
                      />
                    </i>
                  </div>
                ) : (
                  <span className="muted">—</span>
                )}
              </td>
              <td>
                <span
                  className={`badge ${b.status === "PENDING_ASSAY" ? "amber" : b.status === "POOLED" ? "blue" : "green"}`}
                >
                  <i />
                  {b.status === "PENDING_ASSAY"
                    ? "Scan needed"
                    : b.status === "POOLED"
                      ? "Transport booked"
                      : cropName(b.status.replaceAll("_", " "))}
                </span>
              </td>
              <td>
                <button
                  className="icon-btn"
                  title={
                    b.status === "PENDING_ASSAY"
                      ? "Scan batch"
                      : "View batch passport"
                  }
                  onClick={() =>
                    b.status === "PENDING_ASSAY" ? openScan(b) : batchDetails(b)
                  }
                >
                  <ArrowUpRight size={19} />
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {!batches.length && (
        <div className="empty">
          <Package />
          <h3>Your next harvest starts here</h3>
          <p>Add your first batch to track quality and freshness.</p>
          <button className="btn primary" onClick={() => setModal("batch")}>
            Add a batch <Plus size={16} />
          </button>
        </div>
      )}
    </div>
  );
  return (
    <div className="app-shell">
      <aside className={`sidebar ${sidebar ? "is-open" : ""}`}>
        <a className="brand" href="/farmer">
          <div className="brand-icon">
            <Sprout size={28} />
          </div>
          <span>
            FarmPool<span className="brand-360">360</span>
            <small>GROW BETTER. GO TOGETHER.</small>
          </span>
        </a>
        <div className="workspace-label">YOUR FARM, CONNECTED</div>
        <nav>
          {links.map((l) => (
            <button
              key={l.view}
              className={`nav-link ${view === l.view ? "active" : ""}`}
              onClick={() => go(l.view)}
            >
              <l.icon size={20} />
              <span>{t[l.view]}</span>
              {l.view === "scan" && pending > 0 && <em>{pending}</em>}
              {view === l.view && <span className="nav-active-dot" />}
            </button>
          ))}
        </nav>
        <div className="sidebar-note">
          <div className="little-leaf">
            <Leaf size={20} />
          </div>
          <h4>
            Small farms.
            <br />
            Bigger possibilities.
          </h4>
          <p>
            Every harvest is better
            <br />
            when we grow together.
          </p>
          <div className="seedling-art">
            ⌁ <Sprout size={66} /> ⌁
          </div>
        </div>
        <div className="sidebar-bottom">
          <button
            className={`nav-link ${view === "settings" ? "active" : ""}`}
            onClick={() => go("settings")}
          >
            <Settings size={19} />
            Settings & help
          </button>
          <div className="powered">
            <span className="pulse-dot" /> POWERED BY CHRONOCROP
          </div>
        </div>
      </aside>
      {sidebar && (
        <div className="mobile-scrim" onClick={() => setSidebar(false)} />
      )}
      <div className="main-shell">
        <header className="topbar">
          <div className="breadcrumbs">
            <button
              className="icon-btn mobile-menu"
              aria-label="Open navigation"
              onClick={() => setSidebar(!sidebar)}
            >
              <Menu />
            </button>
            <span>My workspace</span>
            <ChevronRight size={14} />
            <strong>
              {view === "settings"
                ? "Settings"
                : view === "passport"
                  ? "Bio-Clock passport"
                  : view === "admin"
                    ? "Crop calibration"
                    : t[view]}
            </strong>
          </div>
          <div className="topbar-actions">
            <span className={`connection ${demo ? "demo-mode" : ""}`}>
              <span className="pulse-dot" />
              {demo
                ? "Demo experience"
                : online
                  ? "Backend connected"
                  : "Backend offline"}
            </span>
            <select
              aria-label="Language"
              value={language}
              onChange={(e) => {
                const l = e.target.value as Language;
                setLanguage(l);
                if (!demo)
                  run(async () => {
                    await api("PATCH /users/me", { body: { language: l } });
                  });
              }}
            >
              <option value="EN">English</option>
              <option value="HI">हिन्दी</option>
              <option value="MR">मराठी</option>
              <option value="TA">தமிழ்</option>
            </select>
            <div className="notification-wrap">
              <button
                className="icon-btn notification"
                aria-label="Notifications"
                onClick={() => setNotifications(!notifications)}
              >
                <Bell size={20} />
                <i />
              </button>
              {notifications && (
                <div className="notification-panel">
                  <h3>Your farm updates</h3>
                  <p>
                    <ScanLine size={18} />
                    {pending} batch{pending !== 1 ? "es" : ""} ready for a
                    quality scan.
                  </p>
                  <p>
                    <Truck size={18} />
                    {pools.filter((p) => p.status === "OPEN").length} shared
                    transport pools available.
                  </p>
                  <button
                    className="text-btn"
                    onClick={() => {
                      setNotifications(false);
                      go("batches");
                    }}
                  >
                    View my harvest <ArrowRight size={14} />
                  </button>
                </div>
              )}
            </div>
            <button
              className="avatar"
              aria-label="Open profile settings"
              onClick={() => go("settings")}
            >
              {user.name
                .split(" ")
                .map((s) => s[0])
                .slice(0, 2)
                .join("")}
            </button>
          </div>
        </header>
        <main>
          {demo && (
            <div className="demo-strip">
              <span>
                <Radio size={13} /> Presentation mode · Explore with sample farm
                data
              </span>
              <button onClick={() => setModal("login")}>
                Connect live account <ArrowRight size={13} />
              </button>
            </div>
          )}
          {view === "home" && (
            <>
              <div className="page-intro">
                <div>
                  <div className="eyebrow">
                    <span /> A LITTLE CARE. A BETTER HARVEST.
                  </div>
                  <h1>
                    Your farm at a glance<span className="heading-dot">.</span>
                  </h1>
                  <p>
                    From your first harvest to the last mile. We’re with you.
                  </p>
                </div>
                <div className="date-chip">
                  <CalendarDays size={16} />
                  {new Intl.DateTimeFormat("en-IN", {
                    day: "numeric",
                    month: "short",
                    year: "numeric",
                    timeZone: "Asia/Kolkata",
                  }).format(new Date())}
                </div>
              </div>
              <section className="hero">
                <div className="hero-image" />
                <div className="hero-contours" />
                <div className="hero-copy">
                  <div className="hero-kicker">
                    <span /> ROOTED IN POSSIBILITY
                  </div>
                  <h2>
                    {t.hello},<br />
                    {user.name.split(" ")[0]}{" "}
                    <span className="sun-mark">✺</span>
                  </h2>
                  <p>{t.tagline}</p>
                  <div className="hero-chips">
                    <span>
                      <MapPin size={14} />
                      Nashik, Maharashtra
                    </span>
                    <span>
                      <Sun size={16} />
                      {demo
                        ? "28°C · Sample weather"
                        : "Your harvest, connected"}
                    </span>
                  </div>
                </div>
                <div className="hero-bottom-caption">
                  <Leaf size={15} /> A fresher future starts on your farm.
                </div>
                <div className="hero-pill">
                  <span className="pulse-dot" /> YOUR NEXT GOOD HARVEST STARTS
                  HERE
                </div>
              </section>
              <div className="quick-actions">
                <button className="quick-card mint" onClick={() => openScan()}>
                  <div className="quick-icon">
                    <ScanLine size={27} />
                  </div>
                  <div>
                    <small>SONICASSAY</small>
                    <h3>
                      A little tap.
                      <br />A lot of confidence.
                    </h3>
                    <p>Check fruit quality. No cutting needed.</p>
                  </div>
                  <span className="circle-arrow">
                    <ArrowUpRight size={21} />
                  </span>
                  <div className="wave-decoration">╵╷╽┃╿╽╷╵╷╽┃╿╽</div>
                </button>
                <button
                  className="quick-card forest"
                  onClick={() => go("pools")}
                >
                  <div className="quick-icon">
                    <Truck size={27} />
                  </div>
                  <div>
                    <small>FARMPOOL COLLECTIVE</small>
                    <h3>
                      Same direction.
                      <br />
                      Stronger together.
                    </h3>
                    <p>Find nearby farmers. Share a truck.</p>
                  </div>
                  <span className="circle-arrow">
                    <ArrowUpRight size={21} />
                  </span>
                  <div className="route-decoration">
                    <i />
                    <span>⌁⌁⌁</span>
                    <i />
                  </div>
                </button>
              </div>
              {pending > 0 && (
                <button
                  className="alert-banner"
                  onClick={() => {
                    setFilter("Needs a scan");
                    go("batches");
                  }}
                >
                  <span className="alert-icon">
                    <AlertTriangle size={21} />
                  </span>
                  <span>
                    <strong>A little check goes a long way</strong>
                    <small>
                      {pending} harvest batch
                      {pending > 1 ? "es haven’t" : " hasn’t"} been scanned yet.
                      Let’s make sure it’s market-ready.
                    </small>
                  </span>
                  <span className="alert-action">
                    Check quality <ArrowRight size={16} />
                  </span>
                </button>
              )}
              <div className="stats-grid">
                <Stat
                  icon={<Package />}
                  label="Harvest in your care"
                  value={`${totalKg.toLocaleString("en-IN")}`}
                  unit="kg"
                  note={`${batches.length} active batches`}
                  color="green"
                />
                <Stat
                  icon={<ShieldCheck />}
                  label="Quality-checked batches"
                  value={`${batches.filter((b) => b.qualityGrade).length}`}
                  unit={`/ ${batches.length}`}
                  note="Confidence in every crate"
                  color="sage"
                />
                <Stat
                  icon={<Truck />}
                  label="Shared rides available"
                  value={String(
                    pools.filter((p) => p.status === "OPEN").length,
                  ).padStart(2, "0")}
                  note="Less cost. A lighter footprint."
                  color="gold"
                />
                <Stat
                  icon={<Leaf />}
                  label="Freshness, protected"
                  value={String(
                    Math.round(
                      batches.reduce(
                        (n, b) => n + (b.currentRulHours || 0),
                        0,
                      ) /
                        Math.max(
                          1,
                          batches.filter((b) => b.currentRulHours).length,
                        ),
                    ),
                  )}
                  unit="hrs avg."
                  note="Your harvest’s remaining shelf life"
                  color="peach"
                />
              </div>
              <div className="dashboard-bottom">
                <section className="panel harvest-panel">
                  <div className="panel-heading">
                    <div>
                      <span className="eyebrow">FRESH FROM YOUR FARM</span>
                      <h3>Your recent harvest</h3>
                    </div>
                    <button className="text-btn" onClick={() => go("batches")}>
                      View all <ArrowRight size={15} />
                    </button>
                  </div>
                  {batchTable(true)}
                </section>
                <section className="harvest-tip">
                  <div className="tip-top">
                    <span>
                      <CloudSun size={21} /> HARVEST WINDOW
                    </span>
                    <span className="mini-pill">
                      {demo ? "DEMO INSIGHT" : "PLAN AHEAD"}
                    </span>
                  </div>
                  <h3>
                    Good timing.
                    <br />
                    Great tomatoes.
                  </h3>
                  <p>
                    The right harvest moment means more freshness at the other
                    end.
                  </p>
                  <div className="tip-line">
                    <Sun size={20} />
                    <span>
                      Plan your next harvest
                      <br />
                      <strong>With crop & weather insights</strong>
                    </span>
                  </div>
                  <button onClick={() => go("harvest")}>
                    Find my harvest window <ArrowUpRight size={18} />
                  </button>
                  <Sprout className="tip-sprout" size={115} />
                </section>
              </div>
              <div className="footer-note">
                <Sprout size={15} /> Better for your farm. Better for our
                planet.<span>FarmPool 360 × ChronoCrop</span>
              </div>
            </>
          )}
          {view === "batches" && (
            <>
              <PageIntro
                eyebrow="EVERY CRATE HAS A STORY"
                title="My harvest"
                description="Know your stock. Protect its freshness. Get it moving."
                action={
                  <button
                    className="btn primary"
                    onClick={() => setModal("batch")}
                  >
                    <Plus size={17} />
                    Add harvest batch
                  </button>
                }
              />
              <div className="stats-grid three">
                <Stat
                  icon={<Package />}
                  label="Total harvest"
                  value={String(totalKg)}
                  unit="kg"
                  note={`${batches.length} batches in your care`}
                />
                <Stat
                  icon={<ScanLine />}
                  label="Awaiting quality check"
                  value={String(pending)}
                  note="A few taps to get market-ready"
                  color="gold"
                />
                <Stat
                  icon={<Truck />}
                  label="Ready for the road"
                  value={String(
                    batches.filter((b) => b.status === "GRADED").length,
                  )}
                  note="Quality verified, freshness protected"
                />
              </div>
              <section className="panel">
                <div className="filter-row">
                  <div className="tabs">
                    {[
                      "All batches",
                      "Needs a scan",
                      "Graded",
                      "Transport booked",
                    ].map((s) => (
                      <button
                        className={filter === s ? "active" : ""}
                        onClick={() => setFilter(s)}
                        key={s}
                      >
                        {s}
                      </button>
                    ))}
                  </div>
                  <div className="search">
                    <Search size={17} />
                    <input
                      placeholder="Search produce…"
                      value={search}
                      onChange={(e) => setSearch(e.target.value)}
                    />
                  </div>
                </div>
                {batchTable()}
                <div className="panel-foot">
                  {visibleBatches.length} batches · Freshness calculated from
                  acoustic quality checks
                </div>
              </section>
              <div className="mini-feature">
                <QrCode />
                <span>
                  <strong>A passport for every harvest.</strong> Open a batch to
                  view its shareable Bio-Clock passport.
                </span>
              </div>
            </>
          )}
          {view === "harvest" && (
            <>
              <PageIntro
                eyebrow="HARVESTWINDOW"
                title="Good things take timing."
                description="A little science to help you pick at just the right moment."
              />
              <div className="split-layout">
                <section className="panel form-panel">
                  <h3>Let’s get to know your crop</h3>
                  <p className="muted">
                    Your crop and local conditions, working together.
                  </p>
                  <form
                    onSubmit={(e) => {
                      e.preventDefault();
                      const f = new FormData(e.currentTarget);
                      run(async () => {
                        if (demo) {
                          setDemoAdvice(true);
                          return;
                        }
                        setAdvisory(
                          await api("POST /harvest-advisories", {
                            body: {
                              cropProfileId: String(f.get("crop")),
                              daysSinceFlowering: Number(f.get("days")),
                              targetPickupDate: new Date(
                                String(f.get("pickup")),
                              ).toISOString(),
                              latitude: 20.1667,
                              longitude: 73.9833,
                              simulateRainInHours: rain ? 30 : null,
                            },
                          }),
                        );
                      });
                    }}
                  >
                    <label>
                      What are you growing?
                      <select name="crop">
                        {demo
                          ? [
                              "TOMATO",
                              "MANGO",
                              "CUCUMBER",
                              "POMEGRANATE",
                              "WATERMELON",
                            ].map((c) => <option key={c}>{c}</option>)
                          : crops.map((c) => (
                              <option key={c.id} value={c.id}>
                                {c.displayName[
                                  language.toLowerCase() as "en"
                                ] || c.cropName}
                              </option>
                            ))}
                      </select>
                    </label>
                    <label>
                      Days since flowering
                      <input
                        type="number"
                        name="days"
                        min="0"
                        max="365"
                        defaultValue="65"
                        required
                      />
                    </label>
                    <label>
                      Planned pickup
                      <input
                        type="datetime-local"
                        name="pickup"
                        defaultValue={new Date(Date.now() + 86400000)
                          .toISOString()
                          .slice(0, 16)}
                        required
                      />
                    </label>
                    <div className="location-box">
                      <MapPin size={19} />
                      <span>
                        <strong>Pimpalgaon, Nashik</strong>
                        <small>Farm location · 20.1667° N, 73.9833° E</small>
                      </span>
                      <Check size={17} />
                    </div>
                    <label className="toggle-label">
                      <span>
                        <Droplets size={18} />
                        Simulate rain in 30 hours
                        <small>Explore a demo weather scenario</small>
                      </span>
                      <input
                        type="checkbox"
                        checked={rain}
                        onChange={(e) => setRain(e.target.checked)}
                      />
                    </label>
                    <button disabled={busy} className="btn primary full">
                      {busy ? (
                        <Loader2 className="spin" size={18} />
                      ) : (
                        <CloudSun size={18} />
                      )}
                      Find my harvest window
                    </button>
                  </form>
                </section>
                <div>
                  <div className="weather-card">
                    <div className="eyebrow">
                      {demo ? "SAMPLE FARM CONDITIONS" : "YOUR FARM LOCATION"}
                    </div>
                    <div className="weather-head">
                      <div>
                        <h3>Nashik, Maharashtra</h3>
                        <p>Harvest planning, made simpler</p>
                      </div>
                      <CloudSun size={58} />
                    </div>
                    <div className="weather-metrics">
                      <span>
                        <Sun size={18} />
                        <strong>{demo ? "28°" : "—"}</strong>Temperature
                      </span>
                      <span>
                        <Droplets size={18} />
                        <strong>{demo ? "64%" : "—"}</strong>Humidity
                      </span>
                      <span>
                        <Wind size={18} />
                        <strong>{demo ? "8 km/h" : "—"}</strong>Wind
                      </span>
                    </div>
                  </div>
                  {demoAdvice || advisory ? (
                    <div className="advisory-result">
                      <span className="badge green">
                        <Check size={14} />{" "}
                        {demo ? "SIMULATED RECOMMENDATION" : "HARVEST INSIGHT"}
                      </span>
                      <h2>
                        {advisory
                          ? advisory.effectiveRecommendation.replaceAll(
                              "_",
                              " ",
                            )
                          : rain
                            ? "Harvest before the rain."
                            : "Your harvest window is open."}
                      </h2>
                      <p>
                        {advisory?.explanation ||
                          (rain
                            ? "Rain in the next 30 hours may affect fruit quality. Harvest now and arrange an early pickup."
                            : "Your tomatoes have reached maturity. Harvest in the cooler morning hours to protect their freshness.")}
                      </p>
                      <div className="confidence">
                        <ShieldCheck size={18} />
                        {Math.round((advisory?.confidence || 0.9) * 100)}%
                        confidence
                      </div>
                      <button
                        className="btn primary"
                        onClick={() => setModal("batch")}
                      >
                        Create a harvest batch <ArrowRight size={17} />
                      </button>
                    </div>
                  ) : (
                    <div className="how-card">
                      <Sprout size={34} />
                      <h3>
                        Nature knows.
                        <br />
                        Now you can, too.
                      </h3>
                      <p>
                        We combine crop maturity, your pickup window, and
                        weather risk to find the best moment to harvest.
                      </p>
                      <span>
                        01 Crop maturity <ArrowRight size={14} /> 02 Weather{" "}
                        <ArrowRight size={14} /> 03 Your window
                      </span>
                    </div>
                  )}
                </div>
              </div>
            </>
          )}
          {view === "scan" && (
            <>
              <PageIntro
                eyebrow="SONICASSAY · NON-DESTRUCTIVE QUALITY CHECK"
                title="Listen to your harvest."
                description="Three gentle taps. A clearer picture of what’s inside."
              />
              <div className="split-layout scan-layout">
                <section className="panel scan-panel">
                  <div className="scan-top">
                    <span className="badge green">
                      <ShieldCheck size={13} />{" "}
                      {demo ? "SIMULATED SCAN" : "ACOUSTIC QUALITY SCAN"}
                    </span>
                    <span>16-bit PCM · 44.1 kHz</span>
                  </div>
                  <label className="scan-select">
                    Choose your harvest batch
                    <select
                      value={selected.id}
                      onChange={(e) => {
                        const b = batches.find((b) => b.id === e.target.value);
                        if (b) {
                          setSelected(b);
                          setScanState("idle");
                        }
                      }}
                    >
                      {batches.map((b) => (
                        <option value={b.id} key={b.id}>
                          {cropName(b.cropName)} · {b.weightKg} kg
                        </option>
                      ))}
                    </select>
                  </label>
                  <div
                    className={`scan-orb ${scanState === "recording" ? "recording" : ""}`}
                  >
                    <div className="orb-ring" />
                    <div className="orb-ring second" />
                    <span>
                      {scanState === "done" ? (
                        <Check size={70} />
                      ) : (
                        produce(selected.cropName)
                      )}
                    </span>
                    <span className="orb-dot one" />
                    <span className="orb-dot two" />
                  </div>
                  <h2>
                    {scanState === "done"
                      ? "A good harvest. Verified."
                      : scanState === "recording"
                        ? scanStep
                        : scanState === "processing"
                          ? "Listening to the science…"
                          : "Good quality has a sound."}
                  </h2>
                  <p>
                    {scanState === "done"
                      ? demo
                        ? "Simulated result · your batch is now marked as graded."
                        : "Your acoustic results have been saved to the batch passport."
                      : "Place a fruit on a soft surface. Keep your phone nearby."}
                  </p>
                  <canvas
                    ref={canvas}
                    width={500}
                    height={64}
                    className="wave-canvas"
                  />
                  {scanState === "idle" && (
                    <div className="static-wave">
                      {Array.from({ length: 55 }, (_, i) => (
                        <i
                          key={i}
                          style={{
                            height: `${8 + Math.sin(i * 1.7) ** 2 * 27}px`,
                          }}
                        />
                      ))}
                    </div>
                  )}
                  {scanState === "done" ? (
                    <>
                      <div className="scan-results">
                        <span>
                          <small>QUALITY GRADE</small>
                          <strong>
                            {batches.find((b) => b.id === selected.id)
                              ?.qualityGrade || "A"}
                          </strong>
                        </span>
                        <span>
                          <small>FRESHNESS LEFT</small>
                          <strong>
                            {batches.find((b) => b.id === selected.id)
                              ?.currentRulHours || 72}
                            <em> hrs</em>
                          </strong>
                        </span>
                        <span>
                          <small>CHECK</small>
                          <strong>
                            <ShieldCheck size={28} />
                          </strong>
                        </span>
                      </div>
                      <div className="button-row">
                        <button
                          className="btn primary"
                          onClick={() =>
                            batchDetails(
                              batches.find((b) => b.id === selected.id) ||
                                selected,
                            )
                          }
                        >
                          View batch passport <QrCode size={17} />
                        </button>
                        <button
                          className="btn"
                          onClick={() => {
                            setScanState("idle");
                            go("pools");
                          }}
                        >
                          Find a shared ride <Truck size={17} />
                        </button>
                      </div>
                    </>
                  ) : (
                    <>
                      <button
                        className="btn primary scan-button"
                        onClick={record}
                        disabled={scanState !== "idle" || !batches.length}
                      >
                        {scanState === "idle" ? (
                          <Mic size={19} />
                        ) : (
                          <Loader2 size={19} className="spin" />
                        )}
                        {scanState === "idle"
                          ? demo
                            ? "Try a demo scan"
                            : "Start quality scan"
                          : "Scan in progress…"}
                      </button>
                      <label className="upload-button">
                        <Upload size={14} />
                        Or upload a WAV recording
                        <input
                          type="file"
                          accept=".wav,audio/wav"
                          hidden
                          disabled={demo}
                          onChange={(e) => {
                            const f = e.target.files?.[0];
                            if (f)
                              run(async () => {
                                setScanState("processing");
                                try {
                                  await submitWav(f);
                                } catch (err) {
                                  setScanState("idle");
                                  throw err;
                                }
                              });
                          }}
                        />
                      </label>
                    </>
                  )}
                </section>
                <div>
                  <section className="panel steps-panel">
                    <div className="eyebrow">A LITTLE TAP. NO GUESSWORK.</div>
                    <h3>How to get a great scan</h3>
                    {[
                      [
                        "Find a quiet spot",
                        "Less background noise means a clearer reading.",
                      ],
                      [
                        "Give it three gentle taps",
                        "Tap the fruit’s equator with the same gentle pressure.",
                      ],
                      [
                        "See the quality within",
                        "Get firmness, quality grade, and remaining shelf life.",
                      ],
                    ].map(([a, b], i) => (
                      <div className="instruction" key={a}>
                        <span>0{i + 1}</span>
                        <div>
                          <h4>{a}</h4>
                          <p>{b}</p>
                        </div>
                      </div>
                    ))}
                    <div className="science-note">
                      <Volume2 size={21} />
                      <p>
                        Sound tells a story. Resonant frequency and damping
                        reveal firmness without cutting the fruit.
                      </p>
                    </div>
                  </section>
                  <div className="mini-feature">
                    <Leaf />
                    <span>
                      One fruit checked. The whole batch understood.
                      <small>
                        For representative results, sample fruit from across
                        your batch.
                      </small>
                    </span>
                  </div>
                </div>
              </div>
            </>
          )}
          {view === "pools" && (
            <>
              <PageIntro
                eyebrow="FARMPOOL COLLECTIVE"
                title="A shared road to better returns."
                description="Fill the truck, not the cost. Find a fresh way forward, together."
                action={
                  user.role === "LOGISTICS" ? (
                    <button
                      className="btn primary"
                      onClick={() => setModal("pool")}
                    >
                      <Plus size={17} />
                      Create a pool
                    </button>
                  ) : undefined
                }
              />
              <div className="transport-banner">
                <div>
                  <span className="eyebrow">
                    LESS EMPTY SPACE. MORE POSSIBILITY.
                  </span>
                  <h2>
                    Your neighbour’s harvest.
                    <br />
                    Your shared next mile.
                  </h2>
                  <p>Compatible crops. Smarter routes. Freshness protected.</p>
                </div>
                <div className="truck-art">
                  <Truck size={112} strokeWidth={1} />
                  <span>FARMPOOL COLLECTIVE</span>
                  <div className="road-dots" />
                </div>
              </div>
              <div className="filter-row transport-filter">
                <div>
                  <h3>
                    {matches
                      ? `${matches.length} compatible rides`
                      : "Available shared rides"}
                  </h3>
                  <p className="muted">From the Nashik growing community</p>
                </div>
                <div className="button-row">
                  <select
                    aria-label="Batch for transport"
                    value={selected.id}
                    onChange={(e) => {
                      const b = batches.find((b) => b.id === e.target.value);
                      if (b) setSelected(b);
                    }}
                  >
                    {batches.map((b) => (
                      <option key={b.id} value={b.id}>
                        {cropName(b.cropName)} · {b.weightKg} kg
                      </option>
                    ))}
                  </select>
                  <button
                    className="btn"
                    disabled={busy}
                    onClick={() =>
                      run(async () => {
                        if (demo) {
                          setMatches(
                            pools
                              .filter((p) => p.status === "OPEN")
                              .map((p, i) => ({
                                pool: p,
                                distanceKm: 4 + i * 3,
                                rulDeltaHours: 2,
                                remainingCapacityKg:
                                  p.maxCapacityKg - p.bookedCapacityKg,
                                score: 95 - i * 8,
                              })),
                          );
                        } else {
                          const r = await api("POST /pools/match", {
                            body: { batchId: selected.id },
                          });
                          setMatches(r.matches);
                        }
                      })
                    }
                  >
                    <SlidersHorizontal size={17} />
                    Find my match
                  </button>
                </div>
              </div>
              <div className="pool-grid">
                {(matches ? matches.map((m) => m.pool) : pools).map((p, i) => (
                  <article className="panel pool-card" key={p.id}>
                    <div className="pool-card-top">
                      <span className={`badge ${i === 0 ? "green" : "blue"}`}>
                        <Leaf size={12} />
                        {p.routeTier === "FAST_QCOMM"
                          ? "Fresh & fast"
                          : p.routeTier === "FLEX_REGIONAL"
                            ? "Regional collective"
                            : "Wholesale route"}
                      </span>
                      <span className="muted">
                        {demo
                          ? `${4 + i * 3} km away`
                          : p.status.replaceAll("_", " ")}
                      </span>
                    </div>
                    <div className="pool-route">
                      <div>
                        <MapPin size={18} />
                        <span>
                          <small>FROM</small>
                          <strong>{p.originLabel}</strong>
                        </span>
                      </div>
                      <div className="route-line" />
                      <div>
                        <MapPin size={18} />
                        <span>
                          <small>TO</small>
                          <strong>{p.destinationName}</strong>
                        </span>
                      </div>
                    </div>
                    <div className="carrier">
                      <div>
                        <Truck size={18} />
                      </div>
                      <span>
                        {p.carrierName}
                        <small>
                          <ShieldCheck size={12} /> Community transport partner
                        </small>
                      </span>
                    </div>
                    <div className="capacity-label">
                      <span>
                        {p.bookedCapacityKg.toLocaleString()} /{" "}
                        {p.maxCapacityKg.toLocaleString()} kg
                      </span>
                      <strong>
                        {Math.round(
                          (p.bookedCapacityKg / p.maxCapacityKg) * 100,
                        )}
                        % full
                      </strong>
                    </div>
                    <div className="capacity-bar">
                      <i
                        style={{
                          width: `${Math.min(100, (p.bookedCapacityKg / p.maxCapacityKg) * 100)}%`,
                        }}
                      />
                    </div>
                    <div className="pool-meta">
                      <span>
                        <Users size={15} />
                        {p.memberCount} farmers together
                      </span>
                      <span>
                        <Clock3 size={15} />
                        {new Date(p.pickupWindowStart).toLocaleDateString(
                          "en-IN",
                          { day: "numeric", month: "short" },
                        )}
                      </span>
                    </div>
                    {user.role === "LOGISTICS" ? (
                      <button
                        className="btn primary full"
                        disabled={busy || p.status === "ARRIVED"}
                        onClick={() =>
                          run(async () => {
                            const next =
                              p.status === "OPEN" ? "IN_TRANSIT" : "ARRIVED";
                            if (demo)
                              setPools((ps) =>
                                ps.map((x) =>
                                  x.id === p.id ? { ...x, status: next } : x,
                                ),
                              );
                            else {
                              if (next === "IN_TRANSIT")
                                await api("POST /pools/:poolId/dispatch", {
                                  params: { poolId: p.id },
                                });
                              else
                                await api("POST /pools/:poolId/arrive", {
                                  params: { poolId: p.id },
                                });
                              await load();
                            }
                            notify(
                              next === "IN_TRANSIT"
                                ? "Pool dispatched. Safe travels!"
                                : "Arrival recorded.",
                            );
                          })
                        }
                      >
                        {p.status === "OPEN"
                          ? "Dispatch pool"
                          : p.status === "IN_TRANSIT"
                            ? "Mark arrived"
                            : "Delivered"}
                        <ArrowRight size={16} />
                      </button>
                    ) : (
                      <button
                        className="btn primary full"
                        onClick={() => reserve(p)}
                        disabled={
                          busy ||
                          p.status !== "OPEN" ||
                          batches.some(
                            (b) => b.id === selected.id && b.poolId === p.id,
                          )
                        }
                      >
                        {batches.some(
                          (b) => b.id === selected.id && b.poolId === p.id,
                        )
                          ? "Your space is booked"
                          : "Reserve my space"}{" "}
                        <ArrowRight size={16} />
                      </button>
                    )}
                  </article>
                ))}
              </div>
              <div className="mini-feature">
                <ShieldCheck />
                <span>
                  Freshness comes first.
                  <small>
                    Live matching checks distance, ethylene compatibility,
                    capacity, and remaining shelf life.
                  </small>
                </span>
              </div>
            </>
          )}
          {view === "market" && (
            <>
              <PageIntro
                eyebrow="FROM OUR FARMS, WITH CARE"
                title="Freshness you can believe in."
                description="Quality-verified produce. Transparent prices. A fairer market."
                action={
                  user.role === "FARMER" ? (
                    <button
                      className="btn primary"
                      onClick={() => {
                        setSelected(
                          batches.find((b) => b.qualityGrade) || selected,
                        );
                        setModal("listing");
                      }}
                    >
                      <Plus size={17} />
                      List my produce
                    </button>
                  ) : undefined
                }
              />
              <div className="market-heading">
                <div className="tabs">
                  {["All produce", "Tomato", "Mango", "Pomegranate"].map(
                    (s) => (
                      <button
                        className={
                          search === (s === "All produce" ? "" : s)
                            ? "active"
                            : ""
                        }
                        key={s}
                        onClick={() => setSearch(s === "All produce" ? "" : s)}
                      >
                        {s}
                      </button>
                    ),
                  )}
                </div>
                <span className="market-verified">
                  <ShieldCheck size={16} /> Every harvest. Quality verified.
                </span>
              </div>
              <div className="market-grid">
                {listings
                  .filter(
                    (l) =>
                      l.cropName.toLowerCase().includes(search.toLowerCase()) &&
                      l.availableKg > 0,
                  )
                  .map((l) => (
                    <article className="panel listing-card" key={l.id}>
                      <div
                        className={`listing-art crop-${l.cropName.toLowerCase()}`}
                      >
                        <div className="produce-illustration">
                          <span>{produce(l.cropName)}</span>
                          <span>{produce(l.cropName)}</span>
                          <span>{produce(l.cropName)}</span>
                        </div>
                        <span className="badge green">
                          <ShieldCheck size={13} /> Grade {l.qualityGrade}
                        </span>
                        <span className="listing-local">
                          <MapPin size={12} /> Nashik grown
                        </span>
                      </div>
                      <div className="listing-body">
                        <div className="listing-title">
                          <h3>
                            Farm-fresh {cropName(l.cropName).toLowerCase()}
                          </h3>
                          <span>
                            {money(l.pricePerKgInr)}
                            <small>/ kg</small>
                          </span>
                        </div>
                        <p>
                          <Sprout size={14} />
                          {l.farmerName} · Local farm collective
                        </p>
                        <div className="listing-metrics">
                          <span>
                            <Clock3 size={16} />
                            <strong>{l.guaranteedArrivalRulHours} hrs</strong>
                            arrival freshness
                          </span>
                          <span>
                            <Package size={16} />
                            <strong>{l.availableKg} kg</strong>available
                          </span>
                        </div>
                        <button
                          className="btn full"
                          onClick={() => {
                            setSelectedListing(l);
                            if (user.role === "FARMER") {
                              batchDetails(
                                batches.find((b) => b.id === l.batchId) ||
                                  selected,
                              );
                            } else setModal("order");
                          }}
                        >
                          {user.role === "FARMER"
                            ? "View harvest passport"
                            : "Order this harvest"}
                          <ArrowUpRight size={17} />
                        </button>
                      </div>
                    </article>
                  ))}
              </div>
              {!listings.length && (
                <div className="empty panel">
                  <ShoppingBasket />
                  <h3>A fresh opportunity</h3>
                  <p>
                    Marketplace listings will appear here when farmers list
                    their quality-checked batches.
                  </p>
                </div>
              )}
              <div className="market-promise">
                <Leaf size={28} />
                <div>
                  <h3>Good for the grower. Better for everyone.</h3>
                  <p>
                    No mystery grades. No freshness guesswork. Just good food,
                    moving fairly.
                  </p>
                </div>
              </div>
            </>
          )}
          {view === "orders" && (
            <>
              <PageIntro
                eyebrow="FRESHNESS ON ITS WAY"
                title="Every order, cared for."
                description="Keep your harvest journey in sight, from farm to doorstep."
              />
              <section className="panel">
                <div className="panel-heading">
                  <h3>Your orders</h3>
                  <span className="badge green">{orders.length} orders</span>
                </div>
                {orders.length ? (
                  <div className="table-scroll">
                    <table>
                      <thead>
                        <tr>
                          <th>Harvest</th>
                          <th>Quantity</th>
                          <th>Order value</th>
                          <th>Arrival freshness</th>
                          <th>Status</th>
                          <th></th>
                        </tr>
                      </thead>
                      <tbody>
                        {orders.map((o) => (
                          <tr key={o.id}>
                            <td>
                              <div className="produce-cell">
                                <span className="produce-thumb">
                                  {produce(o.cropName)}
                                </span>
                                <div>
                                  <strong>{cropName(o.cropName)}</strong>
                                  <small>#{o.id.slice(0, 8)}</small>
                                </div>
                              </div>
                            </td>
                            <td>{o.quantityKg} kg</td>
                            <td>{money(o.totalPriceInr)}</td>
                            <td>{o.guaranteedArrivalRulHours} hours</td>
                            <td>
                              <span className="badge green">
                                {o.status.replaceAll("_", " ")}
                              </span>
                            </td>
                            <td>
                              <button
                                className="icon-btn"
                                title="View passport"
                                onClick={() =>
                                  router.push(`/passport/${o.batchId}`)
                                }
                              >
                                <ArrowUpRight size={18} />
                              </button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <div className="empty">
                    <div className="empty-icon">
                      <ShoppingBasket size={45} />
                    </div>
                    <h2>Your next fresh beginning.</h2>
                    <p>
                      {user.role === "FARMER"
                        ? "Orders for your produce will arrive here. Start by listing a quality-checked harvest."
                        : "Find a harvest you love. We’ll keep its whole journey right here."}
                    </p>
                    <button
                      className="btn primary"
                      onClick={() => go("market")}
                    >
                      Explore the marketplace <ArrowRight size={17} />
                    </button>
                  </div>
                )}
              </section>
            </>
          )}
          {view === "passport" && (
            <>
              <PageIntro
                eyebrow="BIO-CLOCK · HARVEST PASSPORT"
                title="A harvest with nothing to hide."
                description="From the first tap to the last mile. Freshness you can trace."
                action={
                  <button className="btn" onClick={() => window.print()}>
                    <Download size={16} />
                    Save passport
                  </button>
                }
              />
              {passport && (
                <div className="passport-grid">
                  <section className="panel passport-main">
                    <div className="passport-title">
                      <span className="produce-large">
                        {produce(passport.batch.cropName)}
                      </span>
                      <div>
                        <span className="eyebrow">VERIFIED HARVEST RECORD</span>
                        <h2>
                          {cropName(passport.batch.cropName)} ·{" "}
                          {passport.batch.weightKg} kg
                        </h2>
                        <p>{passport.batch.farmerName} · Nashik, Maharashtra</p>
                      </div>
                      <span className="grade big">
                        {passport.batch.qualityGrade
                          ? `Grade ${passport.batch.qualityGrade}`
                          : "Scan pending"}
                      </span>
                    </div>
                    <div className="passport-stats">
                      <div>
                        <span>REMAINING FRESHNESS</span>
                        <strong>
                          {passport.batch.currentRulHours ?? "—"}
                          <small> hours</small>
                        </strong>
                        <p>
                          {demo
                            ? "Simulated shelf-life estimate"
                            : "Acoustic shelf-life estimate"}
                        </p>
                      </div>
                      <div>
                        <span>FARM TO MARKET</span>
                        <strong>
                          {passport.batch.status.replaceAll("_", " ")}
                        </strong>
                        <p>Every step, accounted for</p>
                      </div>
                    </div>
                    <h3>The journey of your harvest</h3>
                    <div className="timeline">
                      <div>
                        <span>
                          <Sprout size={19} />
                        </span>
                        <article>
                          <small>01 · FARM ORIGIN</small>
                          <h4>Harvested with care</h4>
                          <p>
                            {passport.batch.farmerName} ·{" "}
                            {new Date(
                              passport.batch.harvestedAt,
                            ).toLocaleDateString("en-IN")}
                          </p>
                        </article>
                        <CircleCheck size={20} />
                      </div>
                      <div>
                        <span>
                          <ScanLine size={19} />
                        </span>
                        <article>
                          <small>02 · SONICASSAY</small>
                          <h4>
                            {passport.batch.qualityGrade
                              ? "Quality checked, without a cut"
                              : "Waiting for its first quality scan"}
                          </h4>
                          <p>
                            {passport.scans.length
                              ? `${passport.scans.length} acoustic scans recorded`
                              : demo
                                ? "Sample quality record for presentation"
                                : "No acoustic scan records yet"}
                          </p>
                        </article>
                        {passport.batch.qualityGrade && (
                          <CircleCheck size={20} />
                        )}
                      </div>
                      <div>
                        <span>
                          <Truck size={19} />
                        </span>
                        <article>
                          <small>03 · SHARED TRANSPORT</small>
                          <h4>
                            {passport.pool?.carrierName ||
                              "The next mile is waiting"}
                          </h4>
                          <p>
                            {passport.pool?.destinationName ||
                              "Book a compatible shared ride to move this harvest."}
                          </p>
                        </article>
                      </div>
                      {passport.scans.map((s) => (
                        <div key={s.id}>
                          <span>
                            <Volume2 size={19} />
                          </span>
                          <article>
                            <small>{s.stage}</small>
                            <h4>
                              {s.f0Hz} Hz · {s.tauMs} ms damping
                            </h4>
                            <p>
                              {new Date(s.recordedAt).toLocaleString("en-IN")}
                            </p>
                          </article>
                        </div>
                      ))}
                    </div>
                    {passport.telemetry.length > 0 && (
                      <>
                        <h3>Temperature history</h3>
                        <div className="temperature-chart">
                          {passport.telemetry.map((r) => (
                            <div key={r.id}>
                              <i
                                style={{
                                  height: `${Math.max(8, r.tempC * 3)}px`,
                                }}
                              />
                              <strong>{r.tempC}°</strong>
                              <small>
                                {new Date(r.recordedAt).toLocaleTimeString(
                                  "en-IN",
                                  { hour: "2-digit", minute: "2-digit" },
                                )}
                              </small>
                            </div>
                          ))}
                        </div>
                      </>
                    )}
                  </section>
                  <section className="panel qr-panel">
                    <div className="eyebrow">ONE HARVEST. ITS WHOLE STORY.</div>
                    <h3>Meet your Bio-Clock</h3>
                    <div className="qr-wrap">
                      <QRCodeSVG
                        value={
                          typeof window === "undefined"
                            ? passport.batch.qrCodeValue
                            : `${window.location.origin}/passport/${passport.batch.id}`
                        }
                        size={196}
                        fgColor="#164d35"
                      />
                    </div>
                    <p>
                      Scan to follow this harvest’s
                      <br />
                      quality and freshness journey.
                    </p>
                    <span className="badge green">
                      <ShieldCheck size={14} />
                      {demo ? "DEMO PASSPORT" : "PUBLIC HARVEST RECORD"}
                    </span>
                    <button
                      className="btn full"
                      onClick={() =>
                        run(async () => {
                          await navigator.clipboard.writeText(
                            window.location.href,
                          );
                          notify("Passport link copied.");
                        })
                      }
                    >
                      Copy passport link <ArrowUpRight size={16} />
                    </button>
                    <small className="muted">
                      {demo
                        ? "Sample records are available on this device. Connect live for a shareable record."
                        : "Publicly accessible. No login needed."}
                    </small>
                  </section>
                </div>
              )}
            </>
          )}
          {(view === "settings" || view === "admin") && (
            <>
              <PageIntro
                eyebrow="MAKE YOURSELF AT HOME"
                title={
                  view === "admin"
                    ? "Crop calibration"
                    : "Your farm. Your preferences."
                }
                description={
                  view === "admin"
                    ? "Review the science behind your crop quality checks."
                    : "A workspace that feels a little more like you."
                }
              />
              <div className="split-layout">
                <section className="panel form-panel">
                  <div className="profile-heading">
                    <span className="avatar large">
                      {user.name
                        .split(" ")
                        .map((s) => s[0])
                        .slice(0, 2)
                        .join("")}
                    </span>
                    <div>
                      <h3>{user.name}</h3>
                      <p>{user.organizationName}</p>
                    </div>
                  </div>
                  <label>
                    Your workspace
                    <select
                      value={user.role}
                      onChange={(e) => changeRole(e.target.value as Role)}
                    >
                      <option value="FARMER">Farmer · grow & sell</option>
                      <option value="LOGISTICS">
                        Logistics · connect & deliver
                      </option>
                      <option value="BUYER">Buyer · source & receive</option>
                      <option value="ADMIN">
                        Agronomist · calibrate & guide
                      </option>
                    </select>
                  </label>
                  <label>
                    Language
                    <select
                      value={language}
                      onChange={(e) => setLanguage(e.target.value as Language)}
                    >
                      <option value="EN">English</option>
                      <option value="HI">हिन्दी · Hindi</option>
                      <option value="MR">मराठी · Marathi</option>
                      <option value="TA">தமிழ் · Tamil</option>
                    </select>
                  </label>
                  <label>
                    Appearance
                    <select
                      value={theme}
                      onChange={(e) => setTheme(e.target.value as Theme)}
                    >
                      <option value="LIGHT">
                        Light · bright as a new morning
                      </option>
                      <option value="DARK">Dark · easy on the eyes</option>
                      <option value="SYSTEM">Follow my device</option>
                    </select>
                  </label>
                  <button
                    className="btn primary"
                    onClick={() =>
                      run(async () => {
                        if (!demo)
                          await api("PATCH /users/me", {
                            body: { language, theme },
                          });
                        notify("Preferences saved. Make yourself at home.");
                      })
                    }
                  >
                    <Check size={17} />
                    Save preferences
                  </button>
                </section>
                <div>
                  <section className="panel form-panel">
                    <span className="eyebrow">YOUR PRESENTATION TOOLKIT</span>
                    <h3>Ready for your next big moment.</h3>
                    <p className="muted">
                      Explore the whole journey with sample data, or connect
                      your live farm account.
                    </p>
                    <div className="setting-row">
                      <span>
                        <strong>
                          {demo
                            ? "Presentation mode is on"
                            : "Live account mode"}
                        </strong>
                        <small>
                          {demo
                            ? "Sample records · no backend changes"
                            : "Connected to the FastAPI backend"}
                        </small>
                      </span>
                      <span className={`badge ${demo ? "amber" : "green"}`}>
                        {demo ? "DEMO" : "LIVE"}
                      </span>
                    </div>
                    <button
                      className="btn full"
                      onClick={() => {
                        if (demo) setModal("login");
                        else {
                          setDemo(true);
                          setBatches(DEMO_BATCHES);
                          setPools(DEMO_POOLS);
                          setListings(DEMO_LISTINGS);
                          setOrders([]);
                          setUser(DEMO_USER);
                          notify("Presentation mode enabled.");
                        }
                      }}
                    >
                      {demo
                        ? "Connect a live account"
                        : "Switch to presentation mode"}
                      <ArrowRight size={17} />
                    </button>
                    <button
                      className="text-btn reset-btn"
                      onClick={() => {
                        if (!demo) {
                          tokenStore.clear();
                          setModal("login");
                          return;
                        }
                        setBatches(DEMO_BATCHES);
                        setPools(DEMO_POOLS);
                        setListings(DEMO_LISTINGS);
                        setOrders([]);
                        setUser(DEMO_USER);
                        notify("Demo reset. You’re ready to present.");
                      }}
                    >
                      <RefreshCw size={15} />
                      {demo ? "Reset presentation data" : "Sign out"}
                    </button>
                  </section>
                  <div className="mini-feature">
                    <Sprout />
                    <span>
                      Built for the people who grow our future.
                      <small>FarmPool 360 × ChronoCrop · Contract v1.1.0</small>
                    </span>
                  </div>
                </div>
              </div>
              {view === "admin" && (
                <section className="panel">
                  <div className="panel-heading">
                    <h3>Crop calibration profiles</h3>
                  </div>
                  {demo ? (
                    <div className="crop-profiles">
                      {[
                        "TOMATO",
                        "MANGO",
                        "CUCUMBER",
                        "WATERMELON",
                        "POMEGRANATE",
                      ].map((c) => (
                        <div key={c}>
                          <span>{produce(c)}</span>
                          <strong>{cropName(c)}</strong>
                          <small>Acoustic quality · Q10 shelf-life model</small>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="crop-profiles">
                      {crops.map((c) => (
                        <div key={c.id}>
                          <span>{produce(c.cropName)}</span>
                          <strong>{c.cropName}</strong>
                          <small>
                            Q10 {c.q10} · Reference {c.referenceTempC}°C
                          </small>
                        </div>
                      ))}
                    </div>
                  )}
                </section>
              )}
            </>
          )}
        </main>
      </div>
      {toast && (
        <div className="toast" role="status">
          <CircleCheck size={20} />
          <span>{toast}</span>
          <button aria-label="Dismiss" onClick={() => setToast("")}>
            <X size={16} />
          </button>
        </div>
      )}
      {modal && (
        <div
          className="modal-backdrop"
          onClick={(e) => {
            if (e.target === e.currentTarget) setModal(null);
          }}
        >
          <section
            className="modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="modal-title"
          >
            <button
              className="modal-close icon-btn"
              aria-label="Close dialog"
              onClick={() => setModal(null)}
            >
              <X />
            </button>
            <div className="modal-icon">
              <Sprout />
            </div>
            <div className="eyebrow">A FRESH START</div>
            <h2 id="modal-title">
              {modal === "batch"
                ? "Fresh from your farm."
                : modal === "listing"
                  ? "Give your harvest a market."
                  : modal === "order"
                    ? "Good produce. Great choice."
                    : modal === "pool"
                      ? "Bring the community together."
                      : modal === "register"
                        ? "Grow with us."
                        : "Welcome to your farm."}
            </h2>
            <p className="muted">
              {modal === "login" || modal === "register"
                ? "Connect to your live farm account. Demo data stays separate."
                : demo
                  ? "Presentation mode · changes are saved on this device."
                  : "Your changes will be saved to your account."}
            </p>
            <form onSubmit={submitForm}>
              {(modal === "login" || modal === "register") && (
                <>
                  {modal === "register" && (
                    <>
                      <label>
                        Your name
                        <input
                          name="name"
                          minLength={2}
                          maxLength={80}
                          required
                          placeholder="Ramesh Pawar"
                        />
                      </label>
                      <label>
                        Your role
                        <select name="role">
                          <option value="FARMER">Farmer</option>
                          <option value="LOGISTICS">Logistics partner</option>
                          <option value="BUYER">Buyer</option>
                        </select>
                      </label>
                      <label>
                        Organization (optional)
                        <input
                          name="organization"
                          minLength={2}
                          maxLength={120}
                        />
                      </label>
                    </>
                  )}
                  <label>
                    Phone number
                    <input
                      type="tel"
                      name="phone"
                      defaultValue={modal === "login" ? "+919800000001" : ""}
                      pattern="\+[1-9][0-9]{9,14}"
                      placeholder="+919800000001"
                      required
                    />
                  </label>
                  <label>
                    Password
                    <input
                      type="password"
                      name="password"
                      minLength={modal === "register" ? 8 : 1}
                      maxLength={72}
                      required
                      defaultValue={modal === "login" ? "Demo@12345" : ""}
                    />
                  </label>
                  {modal === "login" && (
                    <div className="login-hint">
                      <ShieldCheck size={16} />
                      <span>
                        Seeded account prefilled. Password: Demo@12345
                        <br />
                        Farmer: …0001 · Logistics: …0002 · Buyer: …0003
                      </span>
                    </div>
                  )}
                </>
              )}
              {modal === "batch" && (
                <>
                  <label>
                    Crop
                    <select name="crop">
                      {demo
                        ? [
                            "TOMATO",
                            "MANGO",
                            "CUCUMBER",
                            "POMEGRANATE",
                            "WATERMELON",
                          ].map((c) => <option key={c}>{c}</option>)
                        : crops.map((c) => (
                            <option key={c.id} value={c.id}>
                              {cropName(c.cropName)}
                            </option>
                          ))}
                    </select>
                  </label>
                  <div className="form-grid">
                    <label>
                      Total weight (kg)
                      <input
                        type="number"
                        name="weight"
                        min="0.01"
                        max="50000"
                        step="0.01"
                        required
                        defaultValue="250"
                      />
                    </label>
                    <label>
                      Average fruit mass (g)
                      <input
                        type="number"
                        name="mass"
                        min="0.01"
                        max="20000"
                        step="0.01"
                        required
                        defaultValue="120"
                      />
                    </label>
                  </div>
                  <label>
                    Harvested at
                    <input
                      type="datetime-local"
                      name="date"
                      required
                      defaultValue={new Date().toISOString().slice(0, 16)}
                    />
                  </label>
                  <div className="form-grid">
                    <label>
                      Pickup latitude
                      <input
                        type="number"
                        name="latitude"
                        min="-90"
                        max="90"
                        step="any"
                        required
                        defaultValue="20.1667"
                      />
                    </label>
                    <label>
                      Pickup longitude
                      <input
                        type="number"
                        name="longitude"
                        min="-180"
                        max="180"
                        step="any"
                        required
                        defaultValue="73.9833"
                      />
                    </label>
                  </div>
                </>
              )}
              {modal === "listing" && (
                <>
                  <label>
                    Harvest batch
                    <select
                      value={selected.id}
                      onChange={(e) => {
                        const b = batches.find((b) => b.id === e.target.value);
                        if (b) setSelected(b);
                      }}
                    >
                      {batches
                        .filter((b) => b.qualityGrade)
                        .map((b) => (
                          <option key={b.id} value={b.id}>
                            {cropName(b.cropName)} · {b.weightKg} kg
                          </option>
                        ))}
                    </select>
                  </label>
                  <label>
                    Quantity to list (kg)
                    <input
                      name="quantity"
                      type="number"
                      min="0.01"
                      max={selected.weightKg}
                      step="0.01"
                      defaultValue={selected.weightKg}
                      required
                    />
                  </label>
                  <label>
                    Price per kg (₹)
                    <input
                      name="price"
                      type="number"
                      min="0.01"
                      max="100000"
                      step="0.01"
                      defaultValue="32"
                      required
                    />
                  </label>
                </>
              )}
              {modal === "order" && (
                <>
                  <div className="order-preview">
                    <span>{produce(selectedListing.cropName)}</span>
                    <div>
                      <h3>
                        Farm-fresh{" "}
                        {cropName(selectedListing.cropName).toLowerCase()}
                      </h3>
                      <p>
                        {money(selectedListing.pricePerKgInr)} / kg ·{" "}
                        {selectedListing.availableKg} kg available
                      </p>
                    </div>
                  </div>
                  <label>
                    How much would you like? (kg)
                    <input
                      name="quantity"
                      type="number"
                      min="0.01"
                      max={selectedListing.availableKg}
                      step="0.01"
                      defaultValue={Math.min(50, selectedListing.availableKg)}
                      required
                    />
                  </label>
                  <div className="login-hint">
                    <ShieldCheck size={18} />
                    {selectedListing.guaranteedArrivalRulHours} hours of arrival
                    freshness. No payment is collected.
                  </div>
                </>
              )}
              {modal === "pool" && (
                <>
                  <label>
                    Pickup origin
                    <input
                      name="origin"
                      required
                      minLength={2}
                      maxLength={100}
                      defaultValue="Pimpalgaon, Nashik"
                    />
                  </label>
                  <label>
                    Destination
                    <input
                      name="destination"
                      required
                      minLength={2}
                      maxLength={100}
                      defaultValue="Nashik Road Dark Store"
                    />
                  </label>
                  <label>
                    Truck capacity (kg)
                    <input
                      name="capacity"
                      type="number"
                      min="1"
                      max="40000"
                      defaultValue="2000"
                      required
                    />
                  </label>
                  <div className="form-grid">
                    <label>
                      Pickup from
                      <input
                        type="datetime-local"
                        name="start"
                        required
                        defaultValue={new Date(Date.now() + 86400000)
                          .toISOString()
                          .slice(0, 16)}
                      />
                    </label>
                    <label>
                      Pickup until
                      <input
                        type="datetime-local"
                        name="end"
                        required
                        defaultValue={new Date(Date.now() + 97200000)
                          .toISOString()
                          .slice(0, 16)}
                      />
                    </label>
                  </div>
                </>
              )}
              <button
                className="btn primary full"
                disabled={
                  busy || (modal === "listing" && !selected.qualityGrade)
                }
                type="submit"
              >
                {busy && <Loader2 size={18} className="spin" />}
                {modal === "batch"
                  ? "Add harvest batch"
                  : modal === "listing"
                    ? "Publish listing"
                    : modal === "order"
                      ? "Confirm order"
                      : modal === "pool"
                        ? "Create transport pool"
                        : modal === "register"
                          ? "Create my account"
                          : "Sign in to my farm"}
                <ArrowRight size={17} />
              </button>
            </form>
            {(modal === "login" || modal === "register") && (
              <button
                className="text-btn auth-toggle"
                onClick={() =>
                  setModal(modal === "login" ? "register" : "login")
                }
              >
                {modal === "login"
                  ? "New here? Create an account"
                  : "Already growing with us? Sign in"}
              </button>
            )}
          </section>
        </div>
      )}
    </div>
  );
}
function PageIntro({
  eyebrow,
  title,
  description,
  action,
}: {
  eyebrow: string;
  title: string;
  description: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="page-intro">
      <div>
        <div className="eyebrow">
          <span />
          {eyebrow}
        </div>
        <h1>{title}</h1>
        <p>{description}</p>
      </div>
      {action}
    </div>
  );
}
function Stat({
  icon,
  label,
  value,
  unit,
  note,
  color = "green",
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  unit?: string;
  note: string;
  color?: string;
}) {
  return (
    <section className="stat-card">
      <div className="stat-label">
        <span>{label}</span>
        <span className={`stat-icon ${color}`}>{icon}</span>
      </div>
      <div className="stat-value">
        {value} <small>{unit}</small>
      </div>
      <div className="stat-note">
        <span />
        {note}
      </div>
    </section>
  );
}
