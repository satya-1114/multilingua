import type { AudienceContact, AudienceGroup, AudienceTag } from "@/types/audience";
import type { Organization } from "@/types/organization";
import type { AuditLogEntry } from "@/types/audit";
import type { CommunicationChannel, Gender } from "@/constants/india";
import { COMMUNICATION_CHANNELS, DISTRICTS_BY_STATE, GENDERS, INDIAN_STATES, LANGUAGES, OCCUPATIONS } from "@/constants/india";

/**
 * Deterministic mock data generator for audience, organization, and audit
 * fixtures. Uses a seeded RNG so listings stay stable across renders and
 * hot reloads.
 */

function mulberry32(seed: number) {
  let a = seed;
  return () => {
    a |= 0;
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

const FIRST_NAMES = [
  "Aarav", "Vivaan", "Aditya", "Vihaan", "Arjun", "Sai", "Reyansh", "Ayaan", "Krishna", "Ishaan",
  "Rohan", "Kabir", "Aryan", "Kartik", "Rahul", "Ananya", "Diya", "Aadhya", "Kavya", "Aarohi",
  "Anika", "Navya", "Sara", "Myra", "Riya", "Priya", "Meera", "Isha", "Neha", "Pooja",
  "Rajesh", "Suresh", "Ramesh", "Mahesh", "Anil", "Sunil", "Vikram", "Deepak", "Manoj", "Sanjay",
  "Lakshmi", "Saraswati", "Parvati", "Sita", "Radha", "Gita", "Uma", "Kamala", "Sushila", "Rekha",
];

const LAST_NAMES = [
  "Sharma", "Verma", "Iyer", "Nair", "Menon", "Reddy", "Rao", "Kumar", "Singh", "Patel",
  "Shah", "Gupta", "Agarwal", "Jain", "Mishra", "Pandey", "Choudhury", "Das", "Bose", "Ghosh",
  "Chatterjee", "Banerjee", "Mukherjee", "Naidu", "Pillai", "Krishnan", "Subramanian", "Yadav",
  "Bhat", "Desai", "Kaur", "Sethi", "Malhotra", "Kapoor", "Chopra", "Bhatt", "Trivedi", "Joshi",
];

const ORGANIZATION_SEED: {
  name: string;
  type: Organization["type"];
  city: string;
  state: string;
  website: string;
}[] = [
  { name: "Ministry of Health & Family Welfare", type: "Government", city: "New Delhi", state: "Delhi", website: "mohfw.gov.in" },
  { name: "Karnataka State Public Health", type: "Government", city: "Bengaluru Urban", state: "Karnataka", website: "karunadu.karnataka.gov.in" },
  { name: "Rural Awareness Foundation", type: "NGO / Non-profit", city: "Pune", state: "Maharashtra", website: "ruralawareness.org" },
  { name: "Apollo Community Health", type: "Healthcare", city: "Chennai", state: "Tamil Nadu", website: "apolloch.in" },
  { name: "Delhi Public School Society", type: "Education", city: "New Delhi", state: "Delhi", website: "dpssociety.in" },
  { name: "Odisha Disaster Management Authority", type: "Government", city: "Bhubaneswar", state: "Odisha", website: "osdma.org" },
  { name: "Bharat Krishi Sangathan", type: "NGO / Non-profit", city: "Jaipur", state: "Rajasthan", website: "bharatkrishi.org" },
  { name: "Kerala Education Board", type: "Government", city: "Thiruvananthapuram", state: "Kerala", website: "education.kerala.gov.in" },
  { name: "Reliance Foundation", type: "Enterprise", city: "Mumbai", state: "Maharashtra", website: "reliancefoundation.org" },
  { name: "The Hindu Media Group", type: "Media", city: "Chennai", state: "Tamil Nadu", website: "thehindu.com" },
  { name: "Telangana Rural Development", type: "Government", city: "Hyderabad", state: "Telangana", website: "rd.telangana.gov.in" },
  { name: "Pratham Education Foundation", type: "NGO / Non-profit", city: "Mumbai", state: "Maharashtra", website: "pratham.org" },
];

const TAG_SEED = [
  { name: "Priority", color: "#EF4444" },
  { name: "New Registration", color: "#3B82F6" },
  { name: "Volunteer", color: "#8B5CF6" },
  { name: "High Engagement", color: "#22C55E" },
  { name: "Rural", color: "#F59E0B" },
  { name: "Urban", color: "#0EA5E9" },
  { name: "Field Officer", color: "#EC4899" },
  { name: "Beneficiary", color: "#14B8A6" },
];

const GROUP_SEED = [
  { name: "Field Health Workers", description: "Frontline ANM and ASHA workers across districts.", color: "#2563EB" },
  { name: "Primary School Teachers", description: "Government primary school teachers.", color: "#8B5CF6" },
  { name: "Farmers Union — Karnataka", description: "Registered farmers in Karnataka districts.", color: "#22C55E" },
  { name: "Municipal Corporators", description: "Elected corporators across metro cities.", color: "#F59E0B" },
  { name: "Youth Volunteers", description: "18-25 year old volunteers registered for outreach.", color: "#EC4899" },
];

const rng = mulberry32(20260706);
const pick = <T>(arr: readonly T[]) => arr[Math.floor(rng() * arr.length)] as T;
const digit = () => Math.floor(rng() * 10);
const phone = () => `+91 ${6 + Math.floor(rng() * 4)}${Array.from({ length: 9 }, digit).join("")}`;
const pincode = () => `${1 + Math.floor(rng() * 9)}${digit()}${digit()}${digit()}${digit()}${digit()}`;

function iso(daysAgo: number, jitterHours = 0): string {
  const d = new Date();
  d.setUTCDate(d.getUTCDate() - daysAgo);
  d.setUTCHours(d.getUTCHours() - jitterHours);
  return d.toISOString();
}

export const mockOrganizations: Organization[] = ORGANIZATION_SEED.map((seed, i) => {
  const audienceCount = 800 + Math.floor(rng() * 24_000);
  return {
    id: `org-${i + 1}`,
    name: seed.name,
    slug: seed.name.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/-+$/g, ""),
    type: seed.type,
    website: `https://${seed.website}`,
    email: `contact@${seed.website}`,
    phone: phone(),
    address: `${Math.floor(rng() * 200) + 1}, Main Road`,
    city: seed.city,
    state: seed.state,
    country: "India",
    pincode: pincode(),
    timezone: "Asia/Kolkata",
    languages: ["en", "hi", pick(LANGUAGES).code].filter((v, idx, a) => a.indexOf(v) === idx),
    primaryAdminId: `user-${i + 1}`,
    primaryAdminName: `${pick(FIRST_NAMES)} ${pick(LAST_NAMES)}`,
    status: i % 11 === 0 ? "inactive" : i % 13 === 0 ? "suspended" : "active",
    audienceCount,
    userCount: 4 + Math.floor(rng() * 40),
    campaignCount: Math.floor(rng() * 28),
    brandColor: "#2563EB",
    createdAt: iso(120 + i * 6),
    updatedAt: iso(Math.floor(rng() * 30)),
  };
});

export const mockAudienceTags: AudienceTag[] = TAG_SEED.map((t, i) => ({
  id: `tag-${i + 1}`,
  name: t.name,
  color: t.color,
  audienceCount: 20 + Math.floor(rng() * 400),
  createdAt: iso(60 + i * 3),
}));

export const mockAudienceGroups: AudienceGroup[] = GROUP_SEED.map((g, i) => ({
  id: `grp-${i + 1}`,
  name: g.name,
  description: g.description,
  color: g.color,
  memberCount: 40 + Math.floor(rng() * 800),
  createdAt: iso(90 + i * 5),
  updatedAt: iso(Math.floor(rng() * 20)),
}));

function makeContact(index: number): AudienceContact {
  const firstName = pick(FIRST_NAMES);
  const lastName = pick(LAST_NAMES);
  const state = pick(INDIAN_STATES);
  const districts = DISTRICTS_BY_STATE[state] ?? [state];
  const district = districts[Math.floor(rng() * districts.length)] ?? state;
  const org = pick(mockOrganizations);
  const lang = pick(LANGUAGES).code;
  const channel = pick(COMMUNICATION_CHANNELS).key as CommunicationChannel;
  const gender = pick(GENDERS) as Gender;
  const tagCount = Math.floor(rng() * 3);
  const tags = Array.from(
    new Set(Array.from({ length: tagCount }, () => pick(mockAudienceTags))),
  ).map((t) => ({ id: t.id, name: t.name, color: t.color }));
  const groupCount = Math.floor(rng() * 2);
  const groupIds = Array.from(
    new Set(Array.from({ length: groupCount }, () => pick(mockAudienceGroups).id)),
  );
  const r = rng();
  const status: AudienceContact["status"] =
    r < 0.72 ? "active" : r < 0.85 ? "inactive" : r < 0.94 ? "pending" : "opted_out";
  const createdDaysAgo = Math.floor(rng() * 240);
  return {
    id: `aud-${(index + 1).toString().padStart(5, "0")}`,
    firstName,
    lastName,
    fullName: `${firstName} ${lastName}`,
    email: `${firstName.toLowerCase()}.${lastName.toLowerCase()}${index}@${(org.website ?? "example.org").replace("https://", "")}`.replace(/[^a-z0-9@.]/g, ""),
    phone: phone(),
    alternatePhone: rng() > 0.7 ? phone() : undefined,
    dateOfBirth: new Date(1960 + Math.floor(rng() * 45), Math.floor(rng() * 12), 1 + Math.floor(rng() * 27))
      .toISOString()
      .slice(0, 10),
    gender,
    occupation: pick(OCCUPATIONS),
    organizationId: org.id,
    organizationName: org.name,
    department: pick(["Operations", "Field", "Administration", "Outreach", "Research"]),
    state,
    district,
    city: district,
    address: `${Math.floor(rng() * 500) + 1}, ${pick(["MG Road", "Gandhi Nagar", "Nehru Marg", "Station Road", "Church Street"])}`,
    pincode: pincode(),
    preferredLanguage: lang,
    preferredChannel: channel,
    tags,
    groupIds,
    status,
    notes: rng() > 0.85 ? "Requires assisted onboarding." : undefined,
    consentGiven: rng() > 0.05,
    createdAt: iso(createdDaysAgo, Math.floor(rng() * 24)),
    updatedAt: iso(Math.floor(rng() * createdDaysAgo || 1)),
    deletedAt: null,
  };
}

export const mockAudience: AudienceContact[] = Array.from({ length: 320 }, (_, i) => makeContact(i));

const AUDIT_ACTIONS = ["created", "updated", "deleted", "imported", "exported", "assigned"] as const;
const AUDIT_MODULES = ["audience", "audience_group", "audience_tag", "organization", "user"] as const;
const AUDIT_ACTORS = [
  { id: "user-1", name: "Ananya Iyer" },
  { id: "user-2", name: "Rahul Verma" },
  { id: "user-3", name: "Priya Nair" },
  { id: "user-4", name: "Vikram Reddy" },
  { id: "user-5", name: "Meera Krishnan" },
];

export const mockAuditLogs: AuditLogEntry[] = Array.from({ length: 140 }, (_, i) => {
  const actor = pick(AUDIT_ACTORS);
  const action = pick(AUDIT_ACTIONS);
  const module = pick(AUDIT_MODULES);
  const entity = pick(mockAudience);
  return {
    id: `log-${(i + 1).toString().padStart(5, "0")}`,
    action,
    module,
    entityId: entity.id,
    entityLabel: module === "audience" ? entity.fullName : module === "organization" ? pick(mockOrganizations).name : `${module}-${i}`,
    actorId: actor.id,
    actorName: actor.name,
    ipAddress: `${10 + Math.floor(rng() * 240)}.${Math.floor(rng() * 255)}.${Math.floor(rng() * 255)}.${Math.floor(rng() * 255)}`,
    userAgent: "Mozilla/5.0",
    createdAt: iso(Math.floor(rng() * 45), Math.floor(rng() * 24)),
  };
});
