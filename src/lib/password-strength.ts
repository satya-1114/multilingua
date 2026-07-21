export interface PasswordStrength {
  score: 0 | 1 | 2 | 3 | 4;
  label: "Very weak" | "Weak" | "Fair" | "Strong" | "Excellent";
  checks: { rule: string; passed: boolean }[];
}

export function evaluatePasswordStrength(password: string): PasswordStrength {
  const checks = [
    { rule: "At least 8 characters", passed: password.length >= 8 },
    { rule: "Contains a lowercase letter", passed: /[a-z]/.test(password) },
    { rule: "Contains an uppercase letter", passed: /[A-Z]/.test(password) },
    { rule: "Contains a number", passed: /\d/.test(password) },
    { rule: "Contains a special character", passed: /[^A-Za-z0-9]/.test(password) },
  ];

  const passed = checks.filter((c) => c.passed).length;
  let score: PasswordStrength["score"] = 0;
  if (passed >= 5) score = 4;
  else if (passed === 4) score = 3;
  else if (passed === 3) score = 2;
  else if (passed === 2) score = 1;

  const labels: PasswordStrength["label"][] = [
    "Very weak",
    "Weak",
    "Fair",
    "Strong",
    "Excellent",
  ];

  return { score, label: labels[score], checks };
}
