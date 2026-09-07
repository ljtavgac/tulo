import type { Metadata } from "next";
import RecipeGeneratorClient from "./RecipeGeneratorClient";
import { pagePath } from "@/lib/seo";

const TITLE = "Custom Recipe Generator";
const DESCRIPTION =
  "Tell us what's in your kitchen and get a recipe idea back -- a custom recipe generator built around the ingredients you already have.";
const PATH = pagePath("tool_page", "recipe-generator");

export const metadata: Metadata = {
  title: TITLE,
  description: DESCRIPTION,
  alternates: { canonical: PATH },
  openGraph: { title: TITLE, description: DESCRIPTION, url: PATH },
};

export default function RecipeGeneratorPage() {
  return <RecipeGeneratorClient />;
}
