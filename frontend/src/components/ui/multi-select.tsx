import * as React from "react";
import { X } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { Button } from "@/components/ui/button";

// Utility function for class names
function cn(...classes: (string | boolean | undefined | null)[]) {
  return classes.filter(Boolean).join(" ");
}

export interface MultiSelectOption {
  label: string;
  value: string;
}

interface MultiSelectProps {
  options: MultiSelectOption[];
  selected: string[];
  onChange: (values: string[]) => void;
  placeholder?: string;
  className?: string;
  showSelectAll?: boolean;
}

export function MultiSelect({
  options,
  selected,
  onChange,
  placeholder = "Sélectionner...",
  className,
  showSelectAll = true,
}: MultiSelectProps) {
  const [open, setOpen] = React.useState(false);
  const buttonRef = React.useRef<HTMLButtonElement>(null);

  const handleUnselect = (e: React.MouseEvent, value: string) => {
    e.preventDefault();
    e.stopPropagation();
    onChange(selected.filter((s) => s !== value));
  };

  const handleSelect = (value: string) => {
    if (selected.includes(value)) {
      onChange(selected.filter((s) => s !== value));
    } else {
      onChange([...selected, value]);
    }
    // Don't close the popover for multi-select - keep it open
  };

  const handleSelectAll = () => {
    if (selected.length === options.length) {
      // Deselect all
      onChange([]);
    } else {
      // Select all
      onChange(options.map((opt) => opt.value));
    }
  };

  const allSelected = options.length > 0 && selected.length === options.length;

  const selectedOptions = options.filter((option) =>
    selected.includes(option.value)
  );

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          ref={buttonRef}
          variant="outline"
          role="combobox"
          aria-expanded={open}
          className={cn(
            "w-full justify-between h-auto min-h-[40px]",
            className
          )}
        >
          <div className="flex gap-1 flex-wrap">
            {selected.length === 0 && (
              <span className="text-muted-foreground">{placeholder}</span>
            )}
            {selectedOptions.slice(0, 3).map((option) => (
              <Badge
                variant="secondary"
                key={option.value}
                className="mr-1 mb-1"
              >
                {option.label}
                <span
                  role="button"
                  tabIndex={0}
                  aria-label={`Retirer ${option.label}`}
                  className="ml-1 ring-offset-background rounded-full outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 cursor-pointer inline-flex items-center"
                  onMouseDown={(e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    handleUnselect(e, option.value);
                  }}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                      e.preventDefault();
                      e.stopPropagation();
                      handleUnselect(e as any, option.value);
                    }
                  }}
                >
                  <X className="h-3 w-3 text-muted-foreground hover:text-foreground" />
                </span>
              </Badge>
            ))}
            {selected.length > 3 && (
              <Badge variant="secondary" className="mr-1 mb-1">
                +{selected.length - 3} plus
              </Badge>
            )}
          </div>
        </Button>
      </PopoverTrigger>
      <PopoverContent
        className="p-0"
        align="start"
        style={{ width: buttonRef.current?.offsetWidth }}
        onOpenAutoFocus={(e) => e.preventDefault()}
      >
        <Command shouldFilter={true}>
          <CommandInput placeholder="Rechercher..." />
          <CommandList>
            <CommandEmpty>Aucun résultat trouvé.</CommandEmpty>
            <CommandGroup className="max-h-64 overflow-auto">
              {showSelectAll && options.length > 0 && (
                <CommandItem
                  value="select-all"
                  onSelect={(e) => {
                    e.preventDefault();
                    handleSelectAll();
                    setTimeout(() => setOpen(true), 0);
                  }}
                  onMouseDown={(e) => {
                    if (e.button === 0) {
                      e.preventDefault();
                      e.stopPropagation();
                      handleSelectAll();
                      setTimeout(() => setOpen(true), 0);
                    }
                  }}
                  className="cursor-pointer font-semibold border-b"
                >
                  <div
                    className={cn(
                      "mr-2 flex h-4 w-4 items-center justify-center rounded-sm border border-primary",
                      allSelected
                        ? "bg-primary text-primary-foreground"
                        : "opacity-50 [&_svg]:invisible"
                    )}
                  >
                    <svg
                      className="h-4 w-4"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="2"
                      viewBox="0 0 24 24"
                    >
                      <polyline points="20 6 9 17 4 12" />
                    </svg>
                  </div>
                  <span className="flex-1">
                    {allSelected ? "Tout désélectionner" : "Tout sélectionner"}
                  </span>
                </CommandItem>
              )}
              {options.map((option) => {
                const isSelected = selected.includes(option.value);
                return (
                  <CommandItem
                    key={option.value}
                    value={option.label}
                    onSelect={(currentValue) => {
                      // This fires on keyboard (Enter/Space) and sometimes on click
                      handleSelect(option.value);
                      setTimeout(() => setOpen(true), 0);
                    }}
                    onMouseDown={(e) => {
                      // Explicitly handle mouse clicks - onSelect doesn't always fire on click
                      if (e.button === 0) {
                        // Left mouse button only
                        e.preventDefault();
                        e.stopPropagation();
                        handleSelect(option.value);
                        setTimeout(() => setOpen(true), 0);
                      }
                    }}
                    className="cursor-pointer"
                  >
                    <div
                      className={cn(
                        "mr-2 flex h-4 w-4 items-center justify-center rounded-sm border border-primary",
                        isSelected
                          ? "bg-primary text-primary-foreground"
                          : "opacity-50 [&_svg]:invisible"
                      )}
                    >
                      <svg
                        className="h-4 w-4"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="2"
                        viewBox="0 0 24 24"
                      >
                        <polyline points="20 6 9 17 4 12" />
                      </svg>
                    </div>
                    <span className={cn("flex-1", isSelected && "font-medium")}>
                      {option.label}
                    </span>
                  </CommandItem>
                );
              })}
            </CommandGroup>
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  );
}

// Demo
export default function Demo() {
  const [selected, setSelected] = React.useState<string[]>([]);

  const options: MultiSelectOption[] = [
    { label: "React", value: "react" },
    { label: "Vue", value: "vue" },
    { label: "Angular", value: "angular" },
    { label: "Svelte", value: "svelte" },
    { label: "Next.js", value: "nextjs" },
    { label: "Nuxt.js", value: "nuxtjs" },
  ];

  return (
    <div className="w-full max-w-md mx-auto p-8">
      <div className="space-y-4">
        <h2 className="text-2xl font-bold">MultiSelect Component</h2>
        <MultiSelect
          options={options}
          selected={selected}
          onChange={setSelected}
          placeholder="Sélectionner des frameworks..."
        />
        <div className="text-sm text-muted-foreground">
          Sélectionné: {selected.length > 0 ? selected.join(", ") : "Aucun"}
        </div>
      </div>
    </div>
  );
}
