import PageHeader from "../components/PageHeader";
import { useState } from "react";
import SystemStatusWidget from "../components/SystemStatusWidget";

const tabs = [
  { key: "general", label: "Général" },
  { key: "security", label: "Sécurité" },
  { key: "integrations", label: "Intégrations" },
  { key: "system", label: "Système" },
  { key: "notifications", label: "Notifications" },
  { key: "communication", label: "Communication" },
];

export default function SettingsPage() {
  const [activeTab, setActiveTab] = useState("general");

  return (
    <div className="w-full p-4 sm:p-8 flex flex-col items-center">
      <div className="w-full max-w-3xl">
        <PageHeader title="Paramètres" />
        <div className="bg-white p-6 rounded-xl shadow-md">
          <div className="flex border-b mb-6 gap-2 overflow-x-auto">
            {tabs.map((tab) => (
              <button
                key={tab.key}
                className={`px-4 py-2 font-medium border-b-2 transition-colors whitespace-nowrap ${
                  activeTab === tab.key
                    ? "border-[#38ada9] text-[#38ada9]"
                    : "border-transparent text-gray-500 hover:text-[#3c6382]"
                }`}
                onClick={() => setActiveTab(tab.key)}
              >
                {tab.label}
              </button>
            ))}
          </div>
          <div className="mt-4 min-h-[200px]">
            {activeTab === "general" && <div>Paramètres généraux ici.</div>}
            {activeTab === "security" && <div>Paramètres de sécurité ici.</div>}
            {activeTab === "integrations" && (
              <div>Paramètres d'intégration ici.</div>
            )}
            {activeTab === "system" && (
              <div className="flex flex-col gap-6 items-start">
                <SystemStatusWidget />
                <div>Autres paramètres système ici.</div>
              </div>
            )}
            {activeTab === "notifications" && (
              <div>Paramètres et préférences de notification ici.</div>
            )}
            {activeTab === "communication" && (
              <div>Paramètres de communication et de messagerie ici.</div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
