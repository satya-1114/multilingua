/** Reference data for Indian geography and languages used across the platform. */

export const INDIAN_STATES = [
  "Andhra Pradesh",
  "Assam",
  "Bihar",
  "Chhattisgarh",
  "Delhi",
  "Goa",
  "Gujarat",
  "Haryana",
  "Himachal Pradesh",
  "Jharkhand",
  "Karnataka",
  "Kerala",
  "Madhya Pradesh",
  "Maharashtra",
  "Manipur",
  "Meghalaya",
  "Odisha",
  "Punjab",
  "Rajasthan",
  "Sikkim",
  "Tamil Nadu",
  "Telangana",
  "Tripura",
  "Uttar Pradesh",
  "Uttarakhand",
  "West Bengal",
] as const;

export type IndianState = (typeof INDIAN_STATES)[number];

export const DISTRICTS_BY_STATE: Record<string, string[]> = {
  Karnataka: ["Bengaluru Urban", "Bengaluru Rural", "Mysuru", "Mangaluru", "Hubballi", "Belagavi"],
  Maharashtra: ["Mumbai", "Pune", "Nagpur", "Nashik", "Aurangabad", "Thane"],
  "Tamil Nadu": ["Chennai", "Coimbatore", "Madurai", "Tiruchirappalli", "Salem", "Tirunelveli"],
  Telangana: ["Hyderabad", "Warangal", "Karimnagar", "Nizamabad", "Khammam"],
  "Uttar Pradesh": ["Lucknow", "Kanpur", "Varanasi", "Agra", "Prayagraj", "Meerut", "Noida"],
  Delhi: ["New Delhi", "North Delhi", "South Delhi", "East Delhi", "West Delhi"],
  Kerala: ["Thiruvananthapuram", "Kochi", "Kozhikode", "Thrissur", "Kollam"],
  Gujarat: ["Ahmedabad", "Surat", "Vadodara", "Rajkot", "Gandhinagar"],
  Rajasthan: ["Jaipur", "Jodhpur", "Udaipur", "Kota", "Ajmer"],
  "West Bengal": ["Kolkata", "Howrah", "Siliguri", "Durgapur", "Asansol"],
  Punjab: ["Amritsar", "Ludhiana", "Jalandhar", "Patiala", "Mohali"],
  Haryana: ["Gurugram", "Faridabad", "Panipat", "Ambala", "Karnal"],
  "Madhya Pradesh": ["Bhopal", "Indore", "Jabalpur", "Gwalior", "Ujjain"],
  Bihar: ["Patna", "Gaya", "Bhagalpur", "Muzaffarpur", "Darbhanga"],
  Odisha: ["Bhubaneswar", "Cuttack", "Rourkela", "Berhampur", "Sambalpur"],
};

export function districtsFor(state: string | undefined): string[] {
  if (!state) return [];
  return DISTRICTS_BY_STATE[state] ?? [];
}

export interface LanguageOption {
  code: string;
  label: string;
  script?: string;
}

export const LANGUAGES: LanguageOption[] = [
  { code: "hi", label: "Hindi", script: "Devanagari" },
  { code: "en", label: "English", script: "Latin" },
  { code: "bn", label: "Bengali", script: "Bangla" },
  { code: "te", label: "Telugu", script: "Telugu" },
  { code: "mr", label: "Marathi", script: "Devanagari" },
  { code: "ta", label: "Tamil", script: "Tamil" },
  { code: "gu", label: "Gujarati", script: "Gujarati" },
  { code: "kn", label: "Kannada", script: "Kannada" },
  { code: "ml", label: "Malayalam", script: "Malayalam" },
  { code: "pa", label: "Punjabi", script: "Gurmukhi" },
  { code: "or", label: "Odia", script: "Odia" },
  { code: "as", label: "Assamese", script: "Bangla" },
  { code: "ur", label: "Urdu", script: "Nastaliq" },
];

export const COMMUNICATION_CHANNELS = [
  { key: "sms", label: "SMS" },
  { key: "whatsapp", label: "WhatsApp" },
  { key: "email", label: "Email" },
  { key: "voice", label: "Voice / IVR" },
  { key: "push", label: "Push Notification" },
] as const;

export type CommunicationChannel = (typeof COMMUNICATION_CHANNELS)[number]["key"];

export const GENDERS = ["Male", "Female", "Other", "Prefer not to say"] as const;
export type Gender = (typeof GENDERS)[number];

export const OCCUPATIONS = [
  "Farmer",
  "Teacher",
  "Healthcare Worker",
  "Government Officer",
  "Student",
  "Homemaker",
  "Small Business Owner",
  "Software Engineer",
  "Journalist",
  "Social Worker",
  "Retired",
  "Other",
] as const;

export const TIMEZONES = [
  "Asia/Kolkata",
  "Asia/Dubai",
  "Asia/Singapore",
  "UTC",
  "Europe/London",
  "America/New_York",
  "America/Los_Angeles",
] as const;
