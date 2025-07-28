import PageHeader from "../components/PageHeader";
import { AssignRoleToUser } from "../components/AssignRoleToUser";
import { Button } from "@/components/ui/button";

export default function AssignRolePage() {
  return (
    <div className="w-full p-4 sm:p-8 flex flex-col items-center">
      <div className="w-full max-w-3xl">
        <PageHeader title="Attribuer des rôles">
          <Button className="ml-auto bg-[#38ada9] hover:bg-[#3c6382] text-white">
            + Attribuer un rôle
          </Button>
        </PageHeader>
        <div className="bg-white p-6 rounded-xl shadow-md">
          <AssignRoleToUser />
        </div>
      </div>
    </div>
  );
}
