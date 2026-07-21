import { useState, type InputHTMLAttributes } from "react";
import { Eye, EyeOff } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

interface FormFieldProps extends Omit<InputHTMLAttributes<HTMLInputElement>, "id"> {
  id: string;
  label: string;
  error?: string;
  hint?: string;
  containerClassName?: string;
}

export function FormField({
  id,
  label,
  error,
  hint,
  containerClassName,
  className,
  ...props
}: FormFieldProps) {
  return (
    <div className={cn("space-y-1.5", containerClassName)}>
      <Label htmlFor={id}>{label}</Label>
      <Input
        id={id}
        aria-invalid={!!error}
        aria-describedby={error ? `${id}-error` : hint ? `${id}-hint` : undefined}
        className={cn(error && "border-destructive focus-visible:ring-destructive/40", className)}
        {...props}
      />
      {error ? (
        <p id={`${id}-error`} className="text-xs text-destructive" role="alert">
          {error}
        </p>
      ) : hint ? (
        <p id={`${id}-hint`} className="text-xs text-muted-foreground">
          {hint}
        </p>
      ) : null}
    </div>
  );
}

interface PasswordFieldProps extends FormFieldProps {
  showToggle?: boolean;
}

export function PasswordField({ showToggle = true, ...props }: PasswordFieldProps) {
  const [visible, setVisible] = useState(false);
  return (
    <div className={cn("space-y-1.5", props.containerClassName)}>
      <Label htmlFor={props.id}>{props.label}</Label>
      <div className="relative">
        <Input
          {...props}
          type={visible ? "text" : "password"}
          aria-invalid={!!props.error}
          className={cn(
            "pr-10",
            props.error && "border-destructive focus-visible:ring-destructive/40",
            props.className,
          )}
        />
        {showToggle && (
          <Button
            type="button"
            variant="ghost"
            size="icon"
            className="absolute right-1 top-1/2 h-7 w-7 -translate-y-1/2"
            onClick={() => setVisible((v) => !v)}
            aria-label={visible ? "Hide password" : "Show password"}
            tabIndex={-1}
          >
            {visible ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
          </Button>
        )}
      </div>
      {props.error ? (
        <p className="text-xs text-destructive" role="alert">
          {props.error}
        </p>
      ) : props.hint ? (
        <p className="text-xs text-muted-foreground">{props.hint}</p>
      ) : null}
    </div>
  );
}
