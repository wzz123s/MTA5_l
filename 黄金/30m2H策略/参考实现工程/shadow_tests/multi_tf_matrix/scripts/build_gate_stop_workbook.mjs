import fs from "node:fs/promises";
import path from "node:path";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const root = "F:/use_code/MTA5";
const dataDir = path.join(root, "shadow_tests", "multi_tf_matrix", "data", "validation_20260701");
const outputPath = path.join(dataDir, "组合参数总表_门区间_止损区间_中文.xlsx");

async function readCsv(csvPath) {
  const text = await fs.readFile(csvPath, "utf8");
  const rows = text.replace(/^\uFEFF/, "").trim().split(/\r?\n/).map(parseCsvLine);
  return rows;
}

function parseCsvLine(line) {
  const out = [];
  let current = "";
  let inQuotes = false;
  for (let i = 0; i < line.length; i += 1) {
    const ch = line[i];
    if (ch === '"') {
      if (inQuotes && line[i + 1] === '"') {
        current += '"';
        i += 1;
      } else {
        inQuotes = !inQuotes;
      }
    } else if (ch === "," && !inQuotes) {
      out.push(current);
      current = "";
    } else {
      current += ch;
    }
  }
  out.push(current);
  return out;
}

function toMatrix(rows) {
  return rows.map((row) =>
    row.map((value) => {
      if (value === "") return null;
      const n = Number(value);
      return Number.isFinite(n) && /^-?\d+(\.\d+)?$/.test(value) ? n : value;
    }),
  );
}

function styleSheet(sheet, colCount, rowCount, widths) {
  sheet.showGridLines = false;
  sheet.freezePanes.freezeRows(1);
  const header = sheet.getRangeByIndexes(0, 0, 1, colCount);
  header.format = {
    fill: "#1F4E78",
    font: { bold: true, color: "#FFFFFF" },
    horizontalAlignment: "Center",
    verticalAlignment: "Center",
    wrapText: true,
    borders: { preset: "all", style: "thin", color: "#BFD7EA" },
  };
  const body = sheet.getRangeByIndexes(1, 0, Math.max(rowCount - 1, 1), colCount);
  body.format = {
    borders: { preset: "inside", style: "thin", color: "#D9E2F3" },
    verticalAlignment: "Center",
  };
  sheet.getRangeByIndexes(0, 0, rowCount, colCount).format.borders = {
    preset: "outside",
    style: "thin",
    color: "#9FBAD0",
  };
  widths.forEach((w, idx) => {
    sheet.getRangeByIndexes(0, idx, rowCount, 1).format.columnWidth = w;
  });
}

async function addSheet(workbook, name, csvFile, widths) {
  const rows = await readCsv(path.join(dataDir, csvFile));
  const matrix = toMatrix(rows);
  const sheet = workbook.worksheets.add(name);
  sheet.getRangeByIndexes(0, 0, matrix.length, matrix[0].length).values = matrix;
  styleSheet(sheet, matrix[0].length, matrix.length, widths);
  return sheet;
}

const workbook = Workbook.create();

await addSheet(
  workbook,
  "参数总表",
  "组合参数总表_门区间_止损区间_中文.csv",
  [14, 24, 28, 72, 14, 14, 14, 10, 14, 14, 16, 18, 18, 42, 12, 12, 12, 14],
);
await addSheet(
  workbook,
  "止损范围测试",
  "组合止损范围测试_中文.csv",
  [14, 24, 10, 12, 10, 10, 18, 18, 10, 10, 12, 12, 14, 14, 14, 14],
);
await addSheet(
  workbook,
  "资金指标",
  "组合最终资金指标_中文_utf8.csv",
  [14, 24, 24, 14, 14, 14, 12, 12, 12, 12, 12, 12, 12, 12, 12, 12, 12, 12, 12, 12, 12, 12, 12, 12, 12],
);

const inspect = await workbook.inspect({
  kind: "sheet,table",
  maxChars: 4000,
  tableMaxRows: 6,
  tableMaxCols: 8,
});
console.log(inspect.ndjson);

const preview1 = await workbook.render({ sheetName: "参数总表", autoCrop: "all", scale: 1, format: "png" });
await fs.writeFile(path.join(dataDir, "组合参数总表_预览.png"), new Uint8Array(await preview1.arrayBuffer()));
const preview2 = await workbook.render({ sheetName: "止损范围测试", autoCrop: "all", scale: 1, format: "png" });
await fs.writeFile(path.join(dataDir, "组合止损范围测试_预览.png"), new Uint8Array(await preview2.arrayBuffer()));

const xlsx = await SpreadsheetFile.exportXlsx(workbook);
await xlsx.save(outputPath);
console.log(outputPath);
