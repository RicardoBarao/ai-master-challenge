// Carrega os artefatos gerados pela análise (app/data/*.json) uma vez por instância.
// Leitura via fs (não import) para não fazer o TypeScript inferir tipos de um JSON de MBs.
import "server-only";
import { readFileSync } from "node:fs";
import path from "node:path";
import type { Doc, ModelFile } from "./classifier";

const dataDir = path.join(process.cwd(), "data");
const cache = new Map<string, unknown>();

function load<T>(file: string): T {
  if (!cache.has(file)) cache.set(file, JSON.parse(readFileSync(path.join(dataDir, file), "utf-8")));
  return cache.get(file) as T;
}

export const getModel = () => load<ModelFile>("model.json");
export const getNeighbors = () => load<{ items: Doc[] }>("neighbors.json").items;
export const getHoldout = () => load<{ items: Doc[] }>("holdout.json").items;
