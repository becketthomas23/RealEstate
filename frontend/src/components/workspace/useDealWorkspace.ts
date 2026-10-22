"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { api, del, downloadFile, patch, post } from "@/lib/api";
import { today, valueBucketFor } from "@/lib/format";
import {
  EMPTY_DETAIL,
  type AssumptionSet,
  type CalculationRun,
  type DealDetail,
  type DealForm,
  type Distribution,
  type GridResult,
  type MarketCalibration,
  type PricingResult,
  type SavedRun,
  type ScenarioComparison,
  type SensitivityKey,
  type SensitivityResult,
  type SimulationResult,
  type SimulationVariableRequest,
  type SupportingDetail,
  type WaterfallResult,
  type WorkbookImportResult,
  isPricingResult,
  isSensitivityResult,
  isSimulationResult,
  isWaterfallResult,
} from "@/lib/types";
import { DEFAULT_FORM, formFromInputs, toUnderwritingInputs, versionUnchanged, type VersionMeta } from "@/lib/underwriting";

export type SimulationOptions = {
  drivers: SensitivityKey[];
  confidence: "low" | "medium" | "high";
  distribution: Distribution;
  iterations: number;
};
export type CalibrationOptions = {
  file: File;
  propertyType: string;
  valueBucket: string;
  source: string;
  asOfDate: string;
};
export type WaterfallOptions = {
  preferredReturn: string;
  sponsorShare: string;
  prefBeforeCapital: boolean;
};
export type ExportOptions = {
  includeSimulation: boolean;
  includeSensitivity: boolean;
};

const defaultMeta = (): VersionMeta => ({
  label: "Base case",
  source: "",
  effective_date: today(),
  confidence_level: "medium",
  property_type: "Multifamily",
  value_bucket: valueBucketFor(DEFAULT_FORM.purchase_price),
});

export const hasDetail = (detail: SupportingDetail) =>
  Boolean(
    (detail.property && Object.values(detail.property).some((value) => value !== null && value !== "")) ||
      detail.rent_roll.length ||
      detail.other_income.length ||
      detail.operating_expenses.length ||
      detail.notes,
  );

/** Canonical form of the detail so numerically equal versions compare equal. */
function normalizeDetail(detail: SupportingDetail | null | undefined) {
  if (!detail || !hasDetail(detail)) return null;
  const numeric = (value: string | number | null | undefined) => (value === null || value === undefined || value === "" ? null : String(Number(value)));
  return {
    property: detail.property
      ? {
          name: detail.property.name || null,
          address: detail.property.address || null,
          units: numeric(detail.property.units),
          rentable_square_feet: numeric(detail.property.rentable_square_feet),
          year_built: numeric(detail.property.year_built),
          property_class: detail.property.property_class || null,
        }
      : null,
    rent_roll: detail.rent_roll.map((line) => ({
      unit_type: line.unit_type,
      units: numeric(line.units),
      average_square_feet: numeric(line.average_square_feet),
      current_monthly_rent: numeric(line.current_monthly_rent),
      market_monthly_rent: numeric(line.market_monthly_rent),
    })),
    other_income: detail.other_income.map((line) => ({ category: line.category, annual_amount: numeric(line.annual_amount), note: line.note || null })),
    operating_expenses: detail.operating_expenses.map((line) => ({ category: line.category, annual_amount: numeric(line.annual_amount), note: line.note || null })),
    notes: detail.notes || null,
  };
}

/** Strip empty optional values so the API's strict schema accepts the detail. */
function detailForApi(detail: SupportingDetail): SupportingDetail | null {
  if (!hasDetail(detail)) return null;
  const clean = (value: string | number | null | undefined) => (value === null || value === undefined || value === "" ? null : value);
  return {
    property: detail.property
      ? {
          name: (clean(detail.property.name) as string | null) ?? null,
          address: (clean(detail.property.address) as string | null) ?? null,
          units: detail.property.units ? Number(detail.property.units) : null,
          rentable_square_feet: (clean(detail.property.rentable_square_feet) as string | null) ?? null,
          year_built: detail.property.year_built ? Number(detail.property.year_built) : null,
          property_class: (clean(detail.property.property_class) as string | null) ?? null,
        }
      : null,
    rent_roll: detail.rent_roll
      .filter((line) => line.unit_type.trim() && Number(line.units) > 0)
      .map((line) => ({
        unit_type: line.unit_type.trim(),
        units: Number(line.units),
        average_square_feet: (clean(line.average_square_feet) as string | null) ?? null,
        current_monthly_rent: line.current_monthly_rent || "0",
        market_monthly_rent: (clean(line.market_monthly_rent) as string | null) ?? null,
      })),
    other_income: detail.other_income.filter((line) => line.category.trim()).map((line) => ({ category: line.category.trim(), annual_amount: line.annual_amount || "0", note: (clean(line.note) as string | null) ?? null })),
    operating_expenses: detail.operating_expenses.filter((line) => line.category.trim()).map((line) => ({ category: line.category.trim(), annual_amount: line.annual_amount || "0", note: (clean(line.note) as string | null) ?? null })),
    notes: (clean(detail.notes) as string | null) ?? null,
  };
}

/** All workspace state and actions for one deal. */
export function useDealWorkspace(dealId: string | null) {
  const [deal, setDeal] = useState<DealDetail | null>(null);
  const [loadingDeal, setLoadingDeal] = useState(true);
  const [notFound, setNotFound] = useState(false);
  const [activeSet, setActiveSet] = useState<AssumptionSet | null>(null);
  const [runs, setRuns] = useState<CalculationRun[]>([]);
  const [form, setForm] = useState<DealForm>(DEFAULT_FORM);
  const [meta, setMeta] = useState<VersionMeta>(defaultMeta);
  const [detail, setDetail] = useState<SupportingDetail>(EMPTY_DETAIL);
  const [result, setResult] = useState<PricingResult | null>(null);
  const [sensitivity, setSensitivity] = useState<SensitivityResult | null>(null);
  const [grid, setGrid] = useState<{ x: SensitivityKey; y: SensitivityKey; result: GridResult } | null>(null);
  const [simulation, setSimulation] = useState<SimulationResult | null>(null);
  const [simulationPrice, setSimulationPrice] = useState<string | null>(null);
  const [simulationOptions, setSimulationOptions] = useState<SimulationOptions | null>(null);
  const [waterfall, setWaterfall] = useState<WaterfallResult | null>(null);
  const [waterfallPrice, setWaterfallPrice] = useState<string | null>(null);
  const [calibration, setCalibration] = useState<MarketCalibration | null>(null);
  const [comparison, setComparison] = useState<ScenarioComparison | null>(null);
  const [importWarnings, setImportWarnings] = useState<string[]>([]);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const applySet = useCallback((saved: AssumptionSet) => {
    setActiveSet(saved);
    setMeta({
      label: saved.label,
      source: saved.source ?? "",
      effective_date: saved.effective_date,
      confidence_level: saved.confidence_level,
      property_type: saved.property_type,
      value_bucket: saved.value_bucket,
    });
    setDetail(saved.supporting_detail ? { ...EMPTY_DETAIL, ...saved.supporting_detail } : EMPTY_DETAIL);
    setForm((current) => formFromInputs(saved.underwriting, current));
  }, []);

  const loadHistory = useCallback(async (setId: string, showLatest: boolean) => {
    const found = await api<CalculationRun[]>("/v1/assumption-sets/" + setId + "/calculation-runs");
    setRuns(found);
    if (!showLatest) return;
    const latestSolver = found.find((run) => isPricingResult(run.result));
    const latestSensitivity = found.find((run) => isSensitivityResult(run.result));
    const latestSimulation = found.find((run) => isSimulationResult(run.result));
    const latestWaterfall = found.find((run) => isWaterfallResult(run.result));
    setResult(latestSolver && isPricingResult(latestSolver.result) ? latestSolver.result : null);
    setSensitivity(latestSensitivity && isSensitivityResult(latestSensitivity.result) ? latestSensitivity.result : null);
    setSimulation(latestSimulation && isSimulationResult(latestSimulation.result) ? latestSimulation.result : null);
    setSimulationPrice(latestSimulation?.request?.purchase_price ?? null);
    setWaterfall(latestWaterfall && isWaterfallResult(latestWaterfall.result) ? latestWaterfall.result : null);
    setWaterfallPrice(latestWaterfall?.request?.purchase_price ?? null);
    setGrid(null);
    setComparison(null);
    const constraints = latestSolver?.request;
    if (constraints) {
      setForm((current) => ({
        ...current,
        ...(constraints.target_levered_irr ? { target_levered_irr: constraints.target_levered_irr } : {}),
        ...(constraints.minimum_dscr ? { minimum_dscr: constraints.minimum_dscr } : {}),
      }));
    }
  }, []);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      if (!dealId) {
        setLoadingDeal(false);
        setNotFound(true);
        return;
      }
      setLoadingDeal(true);
      try {
        const opened = await api<DealDetail>("/v1/deals/" + dealId);
        if (cancelled) return;
        setDeal(opened);
        const newest = opened.assumption_sets[0] ?? null;
        if (newest) {
          applySet(newest);
          await loadHistory(newest.id, true);
        } else {
          setActiveSet(null);
          setRuns([]);
          setResult(null);
        }
      } catch (caught) {
        if (cancelled) return;
        const status = (caught as { status?: number }).status;
        if (status === 404) setNotFound(true);
        else setError(caught instanceof Error ? caught.message : "Unable to open the deal.");
      } finally {
        if (!cancelled) setLoadingDeal(false);
      }
    }
    void load();
    return () => {
      cancelled = true;
    };
  }, [dealId, applySet, loadHistory]);

  async function run<T>(key: string, action: () => Promise<T>): Promise<T | undefined> {
    setBusy(key);
    setError(null);
    setNotice(null);
    try {
      return await action();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "The request could not be completed.");
      return undefined;
    } finally {
      setBusy(null);
    }
  }

  const inputsOrNull = useMemo(() => {
    try {
      return toUnderwritingInputs(form);
    } catch {
      return null;
    }
  }, [form]);
  const detailDirty = Boolean(activeSet && JSON.stringify(normalizeDetail(activeSet.supporting_detail)) !== JSON.stringify(normalizeDetail(detail)));
  const dirty = Boolean(activeSet && inputsOrNull && (!versionUnchanged(activeSet, meta, inputsOrNull) || detailDirty));
  const analysisPrice = result?.maximum_purchase_price ?? null;

  const calibratedBounds = (key: SensitivityKey) => {
    const historical = calibration?.driver_ranges.find((item) => item.key === key);
    if (!historical) return {};
    const base = Number(form[key]);
    let minimum = base + Number(historical.percentile_10) - Number(historical.percentile_50);
    let maximum = base + Number(historical.percentile_90) - Number(historical.percentile_50);
    if (key === "exit_cap_rate") minimum = Math.max(minimum, 0.0001);
    if (key === "vacancy_rate" || key === "annual_interest_rate") minimum = Math.max(minimum, 0);
    maximum = Math.min(maximum, 0.9999);
    return minimum < maximum ? { minimum: String(minimum), maximum: String(maximum) } : {};
  };
  const simulationVariables = (options: SimulationOptions): SimulationVariableRequest[] =>
    options.drivers.map((key) => ({ key, confidence_level: options.confidence, confidence_percentage: "50", distribution: options.distribution, ...calibratedBounds(key) }));
  const simulationCorrelations = (options: SimulationOptions) =>
    calibration?.correlations.filter((item) => options.drivers.includes(item.first_key) && options.drivers.includes(item.second_key)) ?? [];

  const openSet = (saved: AssumptionSet) =>
    run("open", async () => {
      applySet(saved);
      await loadHistory(saved.id, true);
    });

  const saveAndSolve = () =>
    run("solve", async () => {
      if (!deal) throw new Error("Open a deal before solving.");
      const underwriting = toUnderwritingInputs(form);
      const unchanged = versionUnchanged(activeSet, meta, underwriting) && !detailDirty;
      const saved = unchanged
        ? (activeSet as AssumptionSet)
        : await post<AssumptionSet>("/v1/deals/" + deal.id + "/assumption-sets", {
            label: meta.label,
            source: meta.source || null,
            effective_date: meta.effective_date,
            confidence_level: meta.confidence_level,
            property_type: meta.property_type,
            value_bucket: meta.value_bucket,
            underwriting,
            supporting_detail: detailForApi(detail),
          });
      const calculation = await post<SavedRun<PricingResult>>("/v1/assumption-sets/" + saved.id + "/maximum-price", {
        target_levered_irr: form.target_levered_irr,
        minimum_dscr: form.minimum_dscr,
      });
      setDeal(await api<DealDetail>("/v1/deals/" + deal.id));
      applySet(saved);
      setResult(calculation.result);
      setSensitivity(null);
      setGrid(null);
      setSimulation(null);
      setWaterfall(null);
      setComparison(null);
      await loadHistory(saved.id, false);
      setNotice(unchanged ? `Inputs unchanged; re-solved v${saved.version} and recorded the run.` : `Saved v${saved.version} (${saved.label}) and solved the maximum price.`);
      return calculation.result;
    });

  const runSensitivity = () =>
    run("sensitivity", async () => {
      if (!activeSet) throw new Error("Save and solve a version first.");
      const calculation = await post<SavedRun<SensitivityResult>>("/v1/assumption-sets/" + activeSet.id + "/sensitivities", {
        target_levered_irr: form.target_levered_irr,
        minimum_dscr: form.minimum_dscr,
      });
      setSensitivity(calculation.result);
      await loadHistory(activeSet.id, false);
    });

  const runGrid = (x: SensitivityKey, y: SensitivityKey) =>
    run("grid", async () => {
      if (x === y) throw new Error("Choose two different drivers.");
      if (!result || !activeSet) throw new Error("Solve the maximum price before running a grid.");
      const base = (key: SensitivityKey) => Number(form[key]);
      const points = (key: SensitivityKey) => {
        const value = base(key);
        const step = key === "exit_cap_rate" ? 0.005 : 0.01;
        return [Math.max(key === "exit_cap_rate" ? 0.0001 : 0, value - step), value, value + step].map((v) => String(parseFloat(v.toPrecision(12))));
      };
      const underwriting = { ...activeSet.underwriting, purchase_price: result.maximum_purchase_price };
      const calculation = await post<GridResult>("/v1/advanced-sensitivities", {
        underwriting,
        dimensions: [
          { key: x, values: points(x) },
          { key: y, values: points(y) },
        ],
        metric: "levered_irr",
      });
      setGrid({ x, y, result: calculation });
    });

  const previewCalibration = (options: CalibrationOptions) =>
    run("calibration", async () => {
      const data = new FormData();
      data.append("file", options.file);
      data.append("property_type", options.propertyType);
      data.append("value_bucket", options.valueBucket);
      data.append("source", options.source);
      data.append("source_as_of_date", options.asOfDate);
      const loaded = await api<MarketCalibration>("/v1/market-calibrations/preview", { method: "POST", body: data });
      setCalibration(loaded);
      setNotice(`Loaded ${loaded.context.observations} historical periods for ${loaded.context.property_type} · ${loaded.context.value_bucket}. The file itself was not saved.`);
    });

  const runSimulation = (options: SimulationOptions) =>
    run("simulation", async () => {
      if (!activeSet) throw new Error("Save and solve a version first.");
      if (!options.drivers.length) throw new Error("Select at least one risk driver.");
      const calculation = await post<SavedRun<SimulationResult>>("/v1/assumption-sets/" + activeSet.id + "/monte-carlo", {
        variables: simulationVariables(options),
        iterations: options.iterations,
        seed: 42,
        target_levered_irr: form.target_levered_irr,
        minimum_dscr: form.minimum_dscr,
        correlations: simulationCorrelations(options),
        market_context: calibration?.context ?? null,
        purchase_price: analysisPrice,
      });
      setSimulation(calculation.result);
      setSimulationPrice(analysisPrice);
      setSimulationOptions(options);
      await loadHistory(activeSet.id, false);
    });

  const runWaterfall = (options: WaterfallOptions) =>
    run("waterfall", async () => {
      if (!activeSet) throw new Error("Save and solve a version first.");
      const calculation = await post<SavedRun<WaterfallResult>>("/v1/assumption-sets/" + activeSet.id + "/waterfall", {
        preferred_return_rate: options.preferredReturn,
        sponsor_residual_share: options.sponsorShare,
        pay_preferred_return_before_capital: options.prefBeforeCapital,
        purchase_price: analysisPrice,
      });
      setWaterfall(calculation.result);
      setWaterfallPrice(analysisPrice);
      await loadHistory(activeSet.id, false);
    });

  const download = (kind: "excel" | "memo", options: ExportOptions = { includeSimulation: false, includeSensitivity: true }) =>
    run("export-" + kind, async () => {
      const underwriting = activeSet ? { ...activeSet.underwriting } : toUnderwritingInputs(form);
      if (result) underwriting.purchase_price = result.maximum_purchase_price;
      const simulationBlock =
        kind === "excel" && options.includeSimulation && simulationOptions
          ? {
              variables: simulationVariables(simulationOptions),
              iterations: simulationOptions.iterations,
              seed: 42,
              correlations: simulationCorrelations(simulationOptions),
              market_context: calibration?.context ?? null,
            }
          : null;
      await downloadFile(
        `/v1/exports/${kind}`,
        {
          ...underwriting,
          report: {
            deal_name: deal?.name ?? null,
            version_label: activeSet ? `v${activeSet.version} · ${activeSet.label}` : meta.label,
            source: meta.source || null,
            effective_date: meta.effective_date,
            confidence_level: meta.confidence_level,
            analysis_basis: result ? "solved maximum supportable price" : "reference purchase price entered in the form",
            target_levered_irr: form.target_levered_irr,
            minimum_dscr: form.minimum_dscr,
            maximum_purchase_price: result?.maximum_purchase_price ?? null,
            recommended_bid_floor: result?.recommended_bid_floor ?? null,
            recommended_bid_ceiling: result?.recommended_bid_ceiling ?? null,
            binding_constraint: result?.binding_constraint ?? null,
          },
          supporting_detail: detailForApi(activeSet?.supporting_detail ? { ...EMPTY_DETAIL, ...activeSet.supporting_detail } : detail),
          ...(kind === "excel" ? { simulation: simulationBlock, include_sensitivity: options.includeSensitivity } : {}),
        },
        kind === "excel" ? slug(deal?.name) + "-underwriting-model.xlsx" : slug(deal?.name) + "-investment-memo.pdf",
      );
    });

  const compareVersions = () =>
    run("compare", async () => {
      if (!deal) return;
      setComparison(
        await post<ScenarioComparison>("/v1/deals/" + deal.id + "/scenario-comparison", {
          target_levered_irr: form.target_levered_irr,
          minimum_dscr: form.minimum_dscr,
        }),
      );
    });

  const importFile = (file: File) =>
    run("import", async () => {
      const data = new FormData();
      data.append("file", file);
      if (/\.xls[xm]$/i.test(file.name)) {
        const imported = await api<WorkbookImportResult>("/v1/imports/underwriting-workbook", { method: "POST", body: data });
        setForm((current) => ({
          ...formFromInputs(imported.underwriting, current),
          ...(imported.targets.target_levered_irr ? { target_levered_irr: imported.targets.target_levered_irr } : {}),
          ...(imported.targets.minimum_dscr ? { minimum_dscr: imported.targets.minimum_dscr } : {}),
        }));
        setDetail({ ...EMPTY_DETAIL, ...imported.supporting_detail });
        setMeta((current) => ({
          ...current,
          label: imported.version.label ?? current.label,
          source: imported.version.source ?? current.source,
          effective_date: imported.version.effective_date ?? current.effective_date,
          confidence_level: imported.version.confidence_level ?? current.confidence_level,
          property_type: imported.version.property_type ?? current.property_type,
          value_bucket: valueBucketFor(imported.underwriting.purchase_price),
        }));
        setImportWarnings(imported.warnings);
        const rolled = Object.entries(imported.sources)
          .filter(([, source]) => source.startsWith("rolled up"))
          .map(([key]) => key.replaceAll("_", " "));
        setNotice(
          `Loaded ${file.name}` +
            (rolled.length ? ` (${rolled.join(" and ")} rolled up from the detail sheets)` : "") +
            ". Review the inputs, then save and solve to create a version.",
        );
      } else {
        const imported = await api<{ underwriting: AssumptionSet["underwriting"] }>("/v1/imports/underwriting", { method: "POST", body: data });
        setForm((current) => formFromInputs(imported.underwriting, current));
        setImportWarnings([]);
        setNotice(`Loaded assumptions from ${file.name}. Review them, then save and solve to create a version.`);
      }
    });

  const renameDeal = (name: string) =>
    run("rename", async () => {
      if (!deal) return;
      const renamed = await patch<DealDetail>("/v1/deals/" + deal.id, { name });
      setDeal({ ...deal, name: renamed.name });
    });

  const deleteDeal = () =>
    run("delete", async () => {
      if (!deal) return;
      await del("/v1/deals/" + deal.id);
      return true;
    });

  const showRun = (saved: CalculationRun) => {
    if (isPricingResult(saved.result)) setResult(saved.result);
    else if (isSensitivityResult(saved.result)) setSensitivity(saved.result);
    else if (isSimulationResult(saved.result)) {
      setSimulation(saved.result);
      setSimulationPrice(saved.request?.purchase_price ?? null);
    } else if (isWaterfallResult(saved.result)) {
      setWaterfall(saved.result);
      setWaterfallPrice(saved.request?.purchase_price ?? null);
    }
  };

  return {
    deal,
    loadingDeal,
    notFound,
    activeSet,
    runs,
    form,
    setForm,
    meta,
    setMeta,
    detail,
    setDetail,
    dirty,
    result,
    analysisPrice,
    sensitivity,
    grid,
    simulation,
    simulationPrice,
    simulationOptions,
    waterfall,
    waterfallPrice,
    calibration,
    comparison,
    importWarnings,
    setImportWarnings,
    busy,
    error,
    setError,
    notice,
    setNotice,
    openSet,
    saveAndSolve,
    runSensitivity,
    runGrid,
    previewCalibration,
    runSimulation,
    runWaterfall,
    download,
    compareVersions,
    importFile,
    renameDeal,
    deleteDeal,
    showRun,
  };
}

export type Workspace = ReturnType<typeof useDealWorkspace>;

const slug = (name: string | null | undefined) =>
  (name ?? "deal")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "") || "deal";
