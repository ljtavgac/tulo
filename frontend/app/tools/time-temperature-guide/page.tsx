import type { Metadata } from "next";
import TimeTemperatureGuideClient from "./TimeTemperatureGuideClient";

const TITLE = "Cooking Time & Temperature Guide";
const DESCRIPTION =
  "Cooking time and temperature guide by protein and method (oven, air fryer, grill), plus USDA safe minimum internal temperatures.";

export const metadata: Metadata = {
  title: TITLE,
  description: DESCRIPTION,
  alternates: { canonical: "/tools/time-temperature-guide" },
  openGraph: { title: TITLE, description: DESCRIPTION, url: "/tools/time-temperature-guide" },
};

export default function TimeTemperatureGuidePage() {
  return <TimeTemperatureGuideClient />;
}
