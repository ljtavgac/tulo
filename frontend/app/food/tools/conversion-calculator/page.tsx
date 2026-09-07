import type { Metadata } from "next";
import ConversionCalculatorClient from "./ConversionCalculatorClient";
import { pagePath } from "@/lib/seo";

const TITLE = "Kitchen Measurement Conversion Calculator";
const DESCRIPTION =
  "Free kitchen measurement conversion calculator -- convert cups, tablespoons, grams, ounces, and oven temperatures between US and metric.";
const PATH = pagePath("tool_page", "conversion-calculator");

export const metadata: Metadata = {
  title: TITLE,
  description: DESCRIPTION,
  alternates: { canonical: PATH },
  openGraph: { title: TITLE, description: DESCRIPTION, url: PATH },
};

export default function ConversionCalculatorPage() {
  return <ConversionCalculatorClient />;
}
