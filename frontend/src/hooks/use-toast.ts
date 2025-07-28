import { toast } from "sonner";

export function useToast() {
  return {
    toast,
    dismiss: toast.dismiss,
    error: toast.error,
    success: toast.success,
    warning: toast.warning,
    info: toast.info,
  };
}
