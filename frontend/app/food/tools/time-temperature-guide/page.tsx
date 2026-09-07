import type { Metadata } from "next";
import TimeTemperatureGuideClient from "./TimeTemperatureGuideClient";
import { pagePath } from "@/lib/seo";

const TITLE = "Cooking Time & Temperature Guide";
const DESCRIPTION =
  "Cooking time and temperature guide by protein and method (oven, air fryer, grill), plus USDA safe minimum internal temperatures.";
const PATH = pagePath("tool_page", "time-temperature-guide");

export const metadata: Metadata = {
  title: TITLE,
  description: DESCRIPTION,
  alternates: { canonical: PATH },
  openGraph: { title: TITLE, description: DESCRIPTION, url: PATH },
};

export default function TimeTemperatureGuidePage() {
  return <TimeTemperatureGuideClient />;
}
