import esbuild from "esbuild";
import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";

const scriptsDir = path.dirname(fileURLToPath(import.meta.url));
const appDir = path.resolve(scriptsDir, "..");
const distDir = path.join(appDir, "dist");
const assetsDir = path.join(distDir, "assets");
const publicDir = path.join(appDir, "public");

async function copyPublicAssets() {
  try {
    await fs.cp(publicDir, distDir, { recursive: true, force: true });
  } catch (error) {
    if (error?.code !== "ENOENT") {
      throw error;
    }
  }
}

async function writeIndexHtml() {
  const sourcePath = path.join(appDir, "index.html");
  const source = await fs.readFile(sourcePath, "utf-8");
  const withScript = source.replace(/<script type="module" src="\/src\/main\.jsx"><\/script>/, '<script type="module" src="/assets/index.js"></script>');
  const withCss = withScript.includes("/assets/index.css")
    ? withScript
    : withScript.replace("</head>", '    <link rel="stylesheet" href="/assets/index.css" />\n  </head>');
  await fs.writeFile(path.join(distDir, "index.html"), withCss, "utf-8");
}

await fs.rm(distDir, { recursive: true, force: true });
await fs.mkdir(assetsDir, { recursive: true });
await copyPublicAssets();

await esbuild.build({
  entryPoints: [path.join(appDir, "src", "main.jsx")],
  bundle: true,
  minify: true,
  sourcemap: true,
  format: "esm",
  target: ["es2020"],
  outfile: path.join(assetsDir, "index.js"),
  loader: {
    ".js": "jsx",
    ".jsx": "jsx",
    ".svg": "file",
    ".png": "file",
    ".jpg": "file",
    ".jpeg": "file",
  },
  define: {
    "process.env.NODE_ENV": '"production"',
  },
});

await writeIndexHtml();
process.stdout.write("Frontend gerado em dist/ com esbuild.\n");
