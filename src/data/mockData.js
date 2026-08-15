export const ACCESS_CODES = {
  AP2024: 'ap',
  CFO2024: 'cfo',
};

export const AGENT_DEFINITIONS = [
  { id: 'parser', name: 'Invoice Parser', icon: 'file-text' },
  { id: 'po', name: 'PO Matcher', icon: 'link' },
  { id: 'duplicate', name: 'Duplicate Detector', icon: 'copy' },
  { id: 'fraud', name: 'Fraud Signal', icon: 'shield' },
  { id: 'risk', name: 'Risk Scorer', icon: 'gauge' },
  { id: 'router', name: 'Approval Router', icon: 'route' },
];

export const initialInvoices = [
  {
    id: '1',
    number: 'INV-2024-441',
    vendor: 'OfficeSupplyCo',
    amount: 800,
    risk: 'LOW',
    status: 'Auto Approved',
    timestamp: '2024-06-14T09:12:00Z',
    agents: [
      { agent: 'Invoice Parser', result: 'Extracted: OfficeSupplyCo, $800, INV-441', confidence: 99, model: 'gpt-3.5-turbo', status: 'pass' },
      { agent: 'PO Matcher', result: 'Matched PO-8821', confidence: 95, model: 'gpt-3.5-turbo', status: 'pass' },
      { agent: 'Duplicate Detector', result: 'No duplicate found', confidence: 97, model: 'gpt-3.5-turbo', status: 'pass' },
      { agent: 'Fraud Signal', result: 'Vendor verified', confidence: 91, model: 'gpt-4o', status: 'pass' },
      { agent: 'Risk Scorer', result: 'Risk: LOW — all checks passed', confidence: 94, model: 'gpt-4o', status: 'pass' },
      { agent: 'Approval Router', result: 'Auto approved', confidence: null, model: 'gpt-3.5-turbo', status: 'route' },
    ],
  },
  {
    id: '2',
    number: 'INV-2024-442',
    vendor: 'TechSoftware Inc',
    amount: 3500,
    risk: 'LOW',
    status: 'Auto Approved',
    timestamp: '2024-06-14T10:30:00Z',
    agents: [
      { agent: 'Invoice Parser', result: 'Extracted: TechSoftware Inc, $3,500, INV-442', confidence: 98, model: 'gpt-3.5-turbo', status: 'pass' },
      { agent: 'PO Matcher', result: 'Matched PO-6612', confidence: 96, model: 'gpt-3.5-turbo', status: 'pass' },
      { agent: 'Duplicate Detector', result: 'No duplicate found', confidence: 97, model: 'gpt-3.5-turbo', status: 'pass' },
      { agent: 'Fraud Signal', result: 'Vendor verified', confidence: 92, model: 'gpt-4o', status: 'pass' },
      { agent: 'Risk Scorer', result: 'Risk: LOW — all checks passed', confidence: 93, model: 'gpt-4o', status: 'pass' },
      { agent: 'Approval Router', result: 'Auto approved', confidence: null, model: 'gpt-3.5-turbo', status: 'route' },
    ],
  },
  {
    id: '3',
    number: 'INV-2024-443',
    vendor: 'CloudServices Ltd',
    amount: 1200,
    risk: 'LOW',
    status: 'Auto Approved',
    timestamp: '2024-06-14T11:45:00Z',
    agents: [
      { agent: 'Invoice Parser', result: 'Extracted: CloudServices Ltd, $1,200, INV-443', confidence: 99, model: 'gpt-3.5-turbo', status: 'pass' },
      { agent: 'PO Matcher', result: 'Matched PO-7734', confidence: 94, model: 'gpt-3.5-turbo', status: 'pass' },
      { agent: 'Duplicate Detector', result: 'No duplicate found', confidence: 98, model: 'gpt-3.5-turbo', status: 'pass' },
      { agent: 'Fraud Signal', result: 'Vendor verified', confidence: 90, model: 'gpt-4o', status: 'pass' },
      { agent: 'Risk Scorer', result: 'Risk: LOW — all checks passed', confidence: 95, model: 'gpt-4o', status: 'pass' },
      { agent: 'Approval Router', result: 'Auto approved', confidence: null, model: 'gpt-3.5-turbo', status: 'route' },
    ],
  },
  {
    id: '4',
    number: 'INV-2024-444',
    vendor: 'PrintingPro',
    amount: 450,
    risk: 'LOW',
    status: 'Auto Approved',
    timestamp: '2024-06-14T13:20:00Z',
    agents: [
      { agent: 'Invoice Parser', result: 'Extracted: PrintingPro, $450, INV-444', confidence: 99, model: 'gpt-3.5-turbo', status: 'pass' },
      { agent: 'PO Matcher', result: 'Matched PO-5543', confidence: 93, model: 'gpt-3.5-turbo', status: 'pass' },
      { agent: 'Duplicate Detector', result: 'No duplicate found', confidence: 97, model: 'gpt-3.5-turbo', status: 'pass' },
      { agent: 'Fraud Signal', result: 'Vendor verified', confidence: 89, model: 'gpt-4o', status: 'pass' },
      { agent: 'Risk Scorer', result: 'Risk: LOW — all checks passed', confidence: 96, model: 'gpt-4o', status: 'pass' },
      { agent: 'Approval Router', result: 'Auto approved', confidence: null, model: 'gpt-3.5-turbo', status: 'route' },
    ],
  },
  {
    id: '5',
    number: 'INV-2024-445',
    vendor: 'TechSoftware Inc',
    amount: 1200,
    risk: 'MEDIUM',
    status: 'Flagged',
    timestamp: '2024-06-14T14:05:00Z',
    agents: [
      { agent: 'Invoice Parser', result: 'Extracted: TechSoftware Inc, $1,200, INV-445', confidence: 98, model: 'gpt-3.5-turbo', status: 'pass' },
      { agent: 'PO Matcher', result: 'Matched PO-6612', confidence: 92, model: 'gpt-3.5-turbo', status: 'pass' },
      { agent: 'Duplicate Detector', result: 'DUPLICATE: INV-9891', confidence: 98, model: 'gpt-3.5-turbo', status: 'fail' },
      { agent: 'Fraud Signal', result: 'Vendor verified', confidence: 88, model: 'gpt-4o', status: 'pass' },
      { agent: 'Risk Scorer', result: 'Risk: MEDIUM — duplicate detected', confidence: 87, model: 'gpt-4o', status: 'warn' },
      { agent: 'Approval Router', result: 'Flagged for review', confidence: null, model: 'gpt-3.5-turbo', status: 'route' },
    ],
  },
  {
    id: '6',
    number: 'INV-2024-446',
    vendor: 'MarketingAgency',
    amount: 8500,
    risk: 'MEDIUM',
    status: 'Flagged',
    timestamp: '2024-06-14T15:30:00Z',
    agents: [
      { agent: 'Invoice Parser', result: 'Extracted: MarketingAgency, $8,500, INV-446', confidence: 97, model: 'gpt-3.5-turbo', status: 'pass' },
      { agent: 'PO Matcher', result: 'No PO found', confidence: 88, model: 'gpt-3.5-turbo', status: 'fail' },
      { agent: 'Duplicate Detector', result: 'No duplicate found', confidence: 96, model: 'gpt-3.5-turbo', status: 'pass' },
      { agent: 'Fraud Signal', result: 'Vendor verified', confidence: 85, model: 'gpt-4o', status: 'pass' },
      { agent: 'Risk Scorer', result: 'Risk: MEDIUM — no PO match', confidence: 82, model: 'gpt-4o', status: 'warn' },
      { agent: 'Approval Router', result: 'Flagged for review', confidence: null, model: 'gpt-3.5-turbo', status: 'route' },
    ],
  },
  {
    id: '7',
    number: 'INV-2024-447',
    vendor: 'GlobalSupplier',
    amount: 15000,
    risk: 'HIGH',
    status: 'Escalated',
    timestamp: '2024-06-14T16:15:00Z',
    agents: [
      { agent: 'Invoice Parser', result: 'Extracted: GlobalSupplier, $15,000, INV-447', confidence: 96, model: 'gpt-3.5-turbo', status: 'pass' },
      { agent: 'PO Matcher', result: 'No PO found', confidence: 85, model: 'gpt-3.5-turbo', status: 'fail' },
      { agent: 'Duplicate Detector', result: 'No duplicate found', confidence: 94, model: 'gpt-3.5-turbo', status: 'pass' },
      { agent: 'Fraud Signal', result: 'New vendor — unverified', confidence: 78, model: 'gpt-4o', status: 'warn' },
      { agent: 'Risk Scorer', result: 'Risk: HIGH — new vendor, large amount', confidence: 84, model: 'gpt-4o', status: 'warn' },
      { agent: 'Approval Router', result: 'Escalated to CFO', confidence: null, model: 'gpt-3.5-turbo', status: 'route' },
    ],
  },
  {
    id: '8',
    number: 'INV-2024-448',
    vendor: 'FastConsult LLC',
    amount: 45000,
    risk: 'CRITICAL',
    status: 'Pending CFO Approval',
    timestamp: '2024-06-14T17:00:00Z',
    riskReasons: ['No PO found', 'Unknown vendor', 'Suspicious bank details'],
    evidence: 'Vendor FastConsult LLC registered 14 days ago. Bank account ACC-999 flagged in fraud database. No purchase order on file. Invoice amount 12x above vendor average.',
    agents: [
      { agent: 'Invoice Parser', result: 'Extracted: FastConsult LLC, $45,000, INV-448', confidence: 95, model: 'gpt-3.5-turbo', status: 'pass' },
      { agent: 'PO Matcher', result: 'No PO found', confidence: 82, model: 'gpt-3.5-turbo', status: 'fail' },
      { agent: 'Duplicate Detector', result: 'No duplicate found', confidence: 93, model: 'gpt-3.5-turbo', status: 'pass' },
      { agent: 'Fraud Signal', result: 'FLAGGED: Unknown vendor, ACC-999', confidence: 96, model: 'gpt-4o', status: 'fail' },
      { agent: 'Risk Scorer', result: 'Risk: CRITICAL', confidence: 98, model: 'gpt-4o', status: 'fail' },
      { agent: 'Approval Router', result: 'Escalated to CFO', confidence: null, model: 'gpt-3.5-turbo', status: 'route' },
    ],
  },
];

export const initialAuditLog = [
  { id: 'a1', timestamp: '2024-06-14T17:00:12Z', invoice: 'INV-2024-448', agent: 'Approval Router', decision: 'Escalated to CFO', model: 'gpt-3.5-turbo', confidence: null, approvedBy: '—' },
  { id: 'a2', timestamp: '2024-06-14T17:00:08Z', invoice: 'INV-2024-448', agent: 'Risk Scorer', decision: 'CRITICAL', model: 'gpt-4o', confidence: 98, approvedBy: '—' },
  { id: 'a3', timestamp: '2024-06-14T17:00:04Z', invoice: 'INV-2024-448', agent: 'Fraud Signal', decision: 'FLAGGED', model: 'gpt-4o', confidence: 96, approvedBy: '—' },
  { id: 'a4', timestamp: '2024-06-14T16:15:45Z', invoice: 'INV-2024-447', agent: 'Approval Router', decision: 'Escalated to CFO', model: 'gpt-3.5-turbo', confidence: null, approvedBy: '—' },
  { id: 'a5', timestamp: '2024-06-14T16:15:40Z', invoice: 'INV-2024-447', agent: 'Risk Scorer', decision: 'HIGH', model: 'gpt-4o', confidence: 84, approvedBy: '—' },
  { id: 'a6', timestamp: '2024-06-14T15:30:22Z', invoice: 'INV-2024-446', agent: 'Approval Router', decision: 'Flagged', model: 'gpt-3.5-turbo', confidence: null, approvedBy: '—' },
  { id: 'a7', timestamp: '2024-06-14T15:30:18Z', invoice: 'INV-2024-446', agent: 'PO Matcher', decision: 'No PO found', model: 'gpt-3.5-turbo', confidence: 88, approvedBy: '—' },
  { id: 'a8', timestamp: '2024-06-14T14:05:33Z', invoice: 'INV-2024-445', agent: 'Approval Router', decision: 'Flagged', model: 'gpt-3.5-turbo', confidence: null, approvedBy: '—' },
  { id: 'a9', timestamp: '2024-06-14T14:05:28Z', invoice: 'INV-2024-445', agent: 'Duplicate Detector', decision: 'DUPLICATE', model: 'gpt-3.5-turbo', confidence: 98, approvedBy: '—' },
  { id: 'a10', timestamp: '2024-06-14T13:20:15Z', invoice: 'INV-2024-444', agent: 'Approval Router', decision: 'Auto Approved', model: 'gpt-3.5-turbo', confidence: null, approvedBy: 'System' },
  { id: 'a11', timestamp: '2024-06-14T11:45:08Z', invoice: 'INV-2024-443', agent: 'Approval Router', decision: 'Auto Approved', model: 'gpt-3.5-turbo', confidence: null, approvedBy: 'System' },
  { id: 'a12', timestamp: '2024-06-14T10:30:42Z', invoice: 'INV-2024-442', agent: 'Approval Router', decision: 'Auto Approved', model: 'gpt-3.5-turbo', confidence: null, approvedBy: 'System' },
  { id: 'a13', timestamp: '2024-06-14T09:12:55Z', invoice: 'INV-2024-441', agent: 'Approval Router', decision: 'Auto Approved', model: 'gpt-3.5-turbo', confidence: null, approvedBy: 'System' },
  { id: 'a14', timestamp: '2024-06-13T16:22:10Z', invoice: 'INV-2024-439', agent: 'Approval Router', decision: 'Auto Approved', model: 'gpt-3.5-turbo', confidence: null, approvedBy: 'System' },
  { id: 'a15', timestamp: '2024-06-13T14:08:33Z', invoice: 'INV-2024-438', agent: 'Risk Scorer', decision: 'LOW', model: 'gpt-4o', confidence: 95, approvedBy: 'System' },
];

export const apStats = {
  total: 47,
  autoApproved: 38,
  flagged: 7,
  blocked: 2,
};

export const cfoStats = {
  totalProcessed: 47,
  autoApproved: 38,
  pendingApproval: 2,
  totalSaved: 46200,
};

export function formatCurrency(amount) {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(amount);
}

export function formatTimestamp(iso) {
  const d = new Date(iso);
  return d.toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
    hour12: true,
  });
}

export function formatAuditTimestamp(iso) {
  const d = new Date(iso);
  return d.toLocaleString('en-US', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  }).replace(',', '');
}

export function generateUploadInvoice(fileName) {
  const risks = ['LOW', 'MEDIUM', 'HIGH'];
  const risk = risks[Math.floor(Math.random() * risks.length)];
  const id = Date.now().toString();
  const num = `INV-2024-${440 + Math.floor(Math.random() * 100)}`;

  const vendorNames = ['DataFlow Inc', 'SecureNet Co', 'BuildRight LLC', 'MediaPulse'];
  const vendor = vendorNames[Math.floor(Math.random() * vendorNames.length)];
  const amount = Math.floor(Math.random() * 5000) + 500;

  const statusMap = {
    LOW: 'Auto Approved',
    MEDIUM: 'Flagged',
    HIGH: 'Escalated',
  };

  const agents = [
    { agent: 'Invoice Parser', result: `Extracted: ${vendor}, $${amount}, ${num}`, confidence: 97 + Math.floor(Math.random() * 3), model: 'gpt-3.5-turbo', status: 'pass' },
    { agent: 'PO Matcher', result: risk === 'LOW' ? 'Matched PO-9901' : 'No PO found', confidence: 90 + Math.floor(Math.random() * 8), model: 'gpt-3.5-turbo', status: risk === 'LOW' ? 'pass' : 'fail' },
    { agent: 'Duplicate Detector', result: 'No duplicate found', confidence: 95 + Math.floor(Math.random() * 4), model: 'gpt-3.5-turbo', status: 'pass' },
    { agent: 'Fraud Signal', result: risk === 'HIGH' ? 'New vendor — unverified' : 'Vendor verified', confidence: 85 + Math.floor(Math.random() * 10), model: 'gpt-4o', status: risk === 'HIGH' ? 'warn' : 'pass' },
    { agent: 'Risk Scorer', result: `Risk: ${risk}`, confidence: 85 + Math.floor(Math.random() * 10), model: 'gpt-4o', status: risk === 'LOW' ? 'pass' : 'warn' },
    { agent: 'Approval Router', result: statusMap[risk], confidence: null, model: 'gpt-3.5-turbo', status: 'route' },
  ];

  return {
    id,
    number: num,
    vendor,
    amount,
    risk,
    status: statusMap[risk],
    timestamp: new Date().toISOString(),
    agents,
    fileName,
  };
}