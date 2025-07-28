import PageHeader from "../components/PageHeader";
import { Button } from "@/components/ui/button";

export default function AnalyticsPage() {
  return (
    <div className="w-full p-4 sm:p-8 flex flex-col items-center">
      <div className="w-full max-w-3xl">
        <PageHeader title="Analytique">
          <Button className="ml-auto bg-[#38ada9] hover:bg-[#3c6382] text-white">
            Voir les rapports
          </Button>
        </PageHeader>
        <div className="bg-white p-6 rounded-xl shadow-md">
          <p className="text-gray-600">Tableau de bord analytique à venir...</p>
        </div>
      </div>
    </div>
  );
}
