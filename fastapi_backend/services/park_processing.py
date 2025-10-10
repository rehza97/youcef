"""
Park Data Processing Service for Parc Corporate NGBSS
Handles data filtering, transformation, and validation rules
"""

import pandas as pd
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, date
import logging
from sqlalchemy.orm import Session
from models.park import Park
from models.dot import DOT

logger = logging.getLogger(__name__)


class ParkDataProcessor:
    """Processes Park data according to Parc Corporate NGBSS rules"""

    def __init__(self, db: Session):
        self.db = db
        self.anomalies = []
        self.processed_count = 0
        self.filtered_count = 0
        self.column_mapping = {}  # Cache for column mappings

    def _find_column(self, df: pd.DataFrame, keywords: list) -> str:
        """Find a column by keywords with improved matching"""
        cache_key = '_'.join(keywords)
        if cache_key in self.column_mapping:
            return self.column_mapping[cache_key]

        # First try exact matches
        for col in df.columns:
            if col in keywords:
                logger.info(f"Found exact column match: '{col}'")
                self.column_mapping[cache_key] = col
                return col

        # Then try partial matches
        for col in df.columns:
            col_lower = col.lower().replace('_', ' ').replace('-', ' ')
            if all(keyword.lower() in col_lower for keyword in keywords):
                logger.info(f"Found column for keywords {keywords}: '{col}'")
                self.column_mapping[cache_key] = col
                return col

        # Try with individual keyword matching (any keyword matches)
        for col in df.columns:
            col_lower = col.lower().replace('_', ' ').replace('-', ' ')
            if any(keyword.lower() in col_lower for keyword in keywords):
                logger.info(
                    f"Found partial column match for keywords {keywords}: '{col}'")
                self.column_mapping[cache_key] = col
                return col

        logger.warning(f"No column found for keywords: {keywords}")
        logger.info(f"Available columns: {list(df.columns)}")
        self.column_mapping[cache_key] = None
        return None

    def process_excel_data(self, file_path: str, progress_callback=None) -> Dict[str, Any]:
        """
        Process Excel file and apply all filtering rules

        Args:
            file_path: Path to the Excel file

        Returns:
            Dict containing processing results and statistics
        """
        try:
            # Read Excel file
            # Assuming CSV format
            df = pd.read_csv(file_path, low_memory=False)
            logger.info(f"Loaded {len(df)} rows from file")

            # Log all column headers
            logger.info(f"File has {len(df.columns)} columns:")
            for i, col in enumerate(df.columns, 1):
                logger.info(f"  {i:2d}. '{col}'")

            # Apply all processing rules
            logger.info("Starting to apply processing rules...")
            logger.info(
                f"Initial dataset: {len(df)} rows, {len(df.columns)} columns")
            df_processed = self._apply_processing_rules(df)
            logger.info(
                f"After processing rules: {len(df_processed)} rows, {len(df_processed.columns)} columns")

            # Generate statistics
            stats = self._generate_statistics(df_processed)

            # Save processed data to database
            logger.info("💾 Saving processed data to database...")
            processed_data = df_processed.to_dict('records')
            save_result = self.save_to_database(
                processed_data, progress_callback)

            if save_result["success"]:
                logger.info(
                    f"✅ Successfully saved {save_result['saved_count']} records to park table")
                if save_result["errors"]:
                    logger.warning(
                        f"⚠️ {len(save_result['errors'])} records failed to save")
            else:
                logger.error(
                    f"❌ Failed to save data to database: {save_result}")

            # Final summary
            logger.info("=" * 60)
            logger.info("PROCESSING SUMMARY")
            logger.info("=" * 60)
            logger.info(
                f"📊 Original file: {len(df):,} rows, {len(df.columns)} columns")
            logger.info(
                f"✅ Processed successfully: {len(df_processed):,} rows")
            logger.info(
                f"🚫 Filtered out: {len(df) - len(df_processed):,} rows")
            logger.info(f"⚠️  Anomalies found: {len(self.anomalies)}")
            logger.info(f"📈 Statistics generated: {len(stats)} categories")
            logger.info(
                f"💾 Database records saved: {save_result.get('saved_count', 0)}")
            logger.info("=" * 60)

            return {
                "success": True,
                "original_rows": len(df),
                "processed_rows": len(df_processed),
                "filtered_rows": len(df) - len(df_processed),
                "anomalies": self.anomalies,
                "statistics": stats,
                "data": processed_data,
                "database_save": save_result
            }

        except Exception as e:
            logger.error(f"Error processing file: {e}")
            return {
                "success": False,
                "error": str(e),
                "original_rows": 0,
                "processed_rows": 0,
                "filtered_rows": 0,
                "anomalies": [],
                "statistics": {}
            }

    def _apply_processing_rules(self, df: pd.DataFrame) -> pd.DataFrame:
        """Apply all processing and filtering rules"""
        original_count = len(df)
        logger.info(f"Starting processing rules with {original_count} rows")

        # 1. Handle DOT and Actel Code relationships
        df = self._process_dot_actel_relationships(df)
        logger.info(
            f"After DOT/Actel processing: {len(df)} rows (removed {original_count - len(df)})")

        # 2. Remove rows with Code Customer L3 = 5 or 57
        df = self._filter_customer_l3(df)
        logger.info(f"After Customer L3 filtering: {len(df)} rows")

        # 3. Remove rows with Offer Type = "Supplementary Offer"
        df = self._filter_offer_type(df)
        logger.info(f"After Offer Type filtering: {len(df)} rows")

        # 4. Handle Moohtarif offers
        df = self._process_moohtarif_offers(df)
        logger.info(f"After Moohtarif processing: {len(df)} rows")

        # 5. Remove rows with Subscriber status = "Predeactivated"
        df = self._filter_subscriber_status(df)
        logger.info(f"After Subscriber Status filtering: {len(df)} rows")

        # 6. Clean and validate data
        df = self._clean_data(df)
        logger.info(f"After data cleaning: {len(df)} rows")

        self.filtered_count = original_count - len(df)
        logger.info(
            f"Filtered out {self.filtered_count} rows, {len(df)} rows remaining")

        return df

    def _process_dot_actel_relationships(self, df: pd.DataFrame) -> pd.DataFrame:
        """Process DOT and Actel Code relationships"""
        logger.info("Processing DOT and Actel Code relationships")

        # Create or get DOTs
        dot_ouargla = self._get_or_create_dot(
            "DOT OUARGLA", "DOT for Ouargla region")
        dot_siege = self._get_or_create_dot(
            "DOT SIEGE", "DOT for Grand Compte")

        # Map Actel Codes to DOTs
        def map_actel_to_dot(actel_code):
            if pd.isna(actel_code):
                return None

            actel_str = str(actel_code)
            if "2B|Centre Algérie Télécom pour les Entreprises HASSI MESSAOUD (2B)" in actel_str:
                return dot_ouargla.id
            elif "99|Grand Compte" in actel_str:
                return dot_siege.id
            return None

        # Apply mapping - handle different column name formats (including real PRK headers)
        actel_column = self._find_column(
            df, ['Actel Code', 'actel', 'Actel Code_Code d\'actel', 'actel_code_code_d_actel'])

        if actel_column:
            df['dot_id'] = df[actel_column].apply(map_actel_to_dot)
            logger.info(f"Applied DOT mapping using column: {actel_column}")
        else:
            logger.warning(
                "No Actel Code column found, assigning default DOT OUARGLA")
            # Assign default DOT OUARGLA for all records without actel code
            df['dot_id'] = dot_ouargla.id

        return df

    def _filter_customer_l3(self, df: pd.DataFrame) -> pd.DataFrame:
        """Remove rows with Code Customer L3 = 5 or 57"""
        logger.info("Filtering out Code Customer L3 = 5 or 57")

        original_count = len(df)

        # Remove rows where Code Customer L3 is 5 or 57
        l3_column = self._find_column(df, ['Code Customer L3', 'level 3'])

        if l3_column:
            df = df[~df[l3_column].isin([5, 57, '5', '57'])]
        else:
            logger.warning(
                "No Code Customer L3 column found, skipping L3 filter")

        filtered_count = original_count - len(df)
        if filtered_count > 0:
            logger.info(
                f"Filtered out {filtered_count} rows with Code Customer L3 = 5 or 57")

        return df

    def _filter_offer_type(self, df: pd.DataFrame) -> pd.DataFrame:
        """Remove rows with Offer Type = 'Supplementary Offer'"""
        logger.info("Filtering out Offer Type = 'Supplementary Offer'")

        original_count = len(df)

        # Remove rows with Supplementary Offer
        offer_type_column = self._find_column(df, ['Offer Type', 'offre'])
        if offer_type_column:
            df = df[df[offer_type_column] != 'Supplementary Offer']
        else:
            logger.warning(
                "No Offer Type column found, skipping offer type filter")

        filtered_count = original_count - len(df)
        if filtered_count > 0:
            logger.info(
                f"Filtered out {filtered_count} rows with Supplementary Offer")

        return df

    def _process_moohtarif_offers(self, df: pd.DataFrame) -> pd.DataFrame:
        """Handle Moohtarif offers - mark as anomalies and remove"""
        logger.info("Processing Moohtarif offers")

        original_count = len(df)

        # Find rows with Moohtarif in Offer name
        offer_name_column = self._find_column(df, ['Offer name', 'offre'])
        if offer_name_column:
            moohtarif_mask = df[offer_name_column].str.contains(
                'Moohtarif', case=False, na=False)
            moohtarif_rows = df[moohtarif_mask]
        else:
            logger.warning(
                "No Offer name column found, skipping Moohtarif processing")
            moohtarif_mask = pd.Series([False] * len(df), index=df.index)
            moohtarif_rows = pd.DataFrame()

        # Add to anomalies
        customer_code_column = self._find_column(df, ['Customer code', 'NCLI'])
        service_number_column = self._find_column(df, ['Service number', 'ND'])

        for _, row in moohtarif_rows.iterrows():
            offer_name = row[offer_name_column] if offer_name_column else 'N/A'
            customer_code = row[customer_code_column] if customer_code_column else 'N/A'
            service_number = row[service_number_column] if service_number_column else 'N/A'

            self.anomalies.append({
                "type": "Parc Corporate NGBSS",
                "description": f"Moohtarif offer found: {offer_name}",
                "customer_code": customer_code,
                "service_number": service_number
            })

        # Remove rows with Moohtarif
        df = df[~moohtarif_mask]

        # Also remove rows with "Solutions Hébergements"
        if offer_name_column:
            df = df[~df[offer_name_column].str.contains(
                'Solutions Hébergements', case=False, na=False)]

        filtered_count = original_count - len(df)
        if filtered_count > 0:
            logger.info(
                f"Filtered out {filtered_count} rows with Moohtarif or Solutions Hébergements")

        return df

    def _filter_subscriber_status(self, df: pd.DataFrame) -> pd.DataFrame:
        """Remove rows with Subscriber status = 'Predeactivated'"""
        logger.info("Filtering out Subscriber status = 'Predeactivated'")

        original_count = len(df)

        # Remove rows with Predeactivated status
        subscriber_status_column = self._find_column(
            df, ['Subscriber status', 'abonne'])
        if subscriber_status_column:
            df = df[df[subscriber_status_column] != 'Predeactivated']
        else:
            logger.warning(
                "No Subscriber status column found, skipping status filter")

        filtered_count = original_count - len(df)
        if filtered_count > 0:
            logger.info(
                f"Filtered out {filtered_count} rows with Predeactivated status")

        return df

    def _clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean and validate data"""
        logger.info("Cleaning and validating data")

        # Convert date columns
        date_columns = [
            'Extraction Date_Date d \'extraction',
            'Status date_Date du statut',
            'Creation Date_Date de creation',
            'Active Date_Date d\'activation',
            'Expiry Date_Date d\'expiration'
        ]

        for col in date_columns:
            if col in df.columns:
                # Try multiple common date formats
                # First try ISO format (YYYY-MM-DD HH:MM:SS)
                parsed = pd.to_datetime(
                    df[col], format='%Y-%m-%d %H:%M:%S', errors='coerce')
                # Then try European format (DD.MM.YYYY HH:MM:SS)
                parsed = parsed.fillna(
                    pd.to_datetime(
                        df[col], format='%d.%m.%Y %H:%M:%S', errors='coerce')
                )
                # Finally, flexible parsing without dayfirst for remaining values
                df[col] = parsed.fillna(
                    pd.to_datetime(df[col], errors='coerce', dayfirst=False)
                )

        # Clean numeric columns
        rental_fees_column = self._find_column(
            df, ['Rental Fees', 'abonnement'])
        if rental_fees_column:
            df[rental_fees_column] = pd.to_numeric(
                df[rental_fees_column], errors='coerce')

        # Remove rows with missing critical data
        customer_code_column = self._find_column(df, ['Customer code', 'NCLI'])
        service_number_column = self._find_column(df, ['Service number', 'ND'])

        if customer_code_column:
            df = df.dropna(subset=[customer_code_column])
        if service_number_column:
            df = df.dropna(subset=[service_number_column])

        return df

    def _get_or_create_dot(self, name: str, description: str = None) -> DOT:
        """Get or create a DOT"""
        dot = self.db.query(DOT).filter(DOT.name == name).first()
        if not dot:
            dot = DOT(
                name=name,
                description=description,
                created_at=datetime.utcnow()
            )
            self.db.add(dot)
            self.db.commit()
            self.db.refresh(dot)
            logger.info(f"Created new DOT: {name}")
        return dot

    def _generate_statistics(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Generate statistics for the processed data"""
        stats = {
            "total_records": len(df),
            "by_dot": {},
            "by_telecom_type": {},
            "by_customer_l2": {},
            "by_customer_l3": {},
            "by_subscriber_status": {},
            "by_offer_type": {}
        }

        # DOT statistics
        if 'dot_id' in df.columns:
            dot_counts = df['dot_id'].value_counts()
            for dot_id, count in dot_counts.items():
                dot = self.db.query(DOT).filter(DOT.id == dot_id).first()
                dot_name = dot.name if dot else f"DOT_{dot_id}"
                stats["by_dot"][dot_name] = int(count)

        # Telecom Type statistics
        telecom_column = self._find_column(df, ['Telecom type', 'SERVICE'])
        if telecom_column:
            telecom_counts = df[telecom_column].value_counts()
            stats["by_telecom_type"] = telecom_counts.to_dict()
        else:
            stats["by_telecom_type"] = {}

        # Customer L2 statistics
        l2_column = self._find_column(df, ['Code Customer L2', 'level 2'])
        if l2_column:
            l2_counts = df[l2_column].value_counts()
            stats["by_customer_l2"] = l2_counts.to_dict()

        # Customer L3 statistics
        l3_column = self._find_column(df, ['Code Customer L3', 'level 3'])
        if l3_column:
            l3_counts = df[l3_column].value_counts()
            stats["by_customer_l3"] = l3_counts.to_dict()

        # Subscriber Status statistics
        subscriber_status_column = self._find_column(
            df, ['Subscriber status', 'abonne'])
        if subscriber_status_column:
            status_counts = df[subscriber_status_column].value_counts()
            stats["by_subscriber_status"] = status_counts.to_dict()

        # Offer Type statistics
        offer_type_column = self._find_column(df, ['Offer Type', 'offre'])
        if offer_type_column:
            offer_counts = df[offer_type_column].value_counts()
            stats["by_offer_type"] = offer_counts.to_dict()

        return stats

    def save_to_database(self, processed_data: List[Dict[str, Any]], progress_callback=None) -> Dict[str, Any]:
        """Save processed data to database with progress tracking"""
        try:
            saved_count = 0
            errors = []
            total_records = len(processed_data)

            logger.info(
                f"💾 Starting database save for {total_records:,} records...")

            for i, record in enumerate(processed_data):
                try:
                    # Map Excel columns to database columns
                    park_record = self._map_to_park_model(record)

                    # Check if record already exists
                    existing = self.db.query(Park).filter(
                        Park.customer_code == park_record.customer_code,
                        Park.service_number == park_record.service_number
                    ).first()

                    if existing:
                        # Update existing record
                        for key, value in park_record.__dict__.items():
                            if not key.startswith('_') and hasattr(existing, key):
                                setattr(existing, key, value)
                        existing.updated_at = datetime.utcnow()
                    else:
                        # Create new record
                        park_record.created_at = datetime.utcnow()
                        self.db.add(park_record)

                    saved_count += 1

                    # Send progress update every 1000 records or at key milestones
                    if progress_callback and (i % 1000 == 0 or i == total_records - 1):
                        progress_percent = int((i + 1) / total_records * 100)
                        progress_callback({
                            "status": "saving",
                            "progress": progress_percent,
                            "message": f"Saving to database... {progress_percent}% ({i + 1:,}/{total_records:,} records)",
                            "saved_count": saved_count,
                            "errors_count": len(errors)
                        })

                except Exception as e:
                    # Use dynamic column detection for error logging
                    temp_df = pd.DataFrame([record])
                    customer_code_col = self._find_column(
                        temp_df, ['Customer code', 'NCLI']) or 'Customer code_NCLI'
                    errors.append({
                        "record": record.get(customer_code_col, 'Unknown'),
                        "error": str(e)
                    })

            self.db.commit()

            # Send final completion update
            if progress_callback:
                progress_callback({
                    "status": "saving_complete",
                    "progress": 100,
                    "message": f"Database save completed! Saved {saved_count:,} records successfully",
                    "saved_count": saved_count,
                    "errors_count": len(errors)
                })

            return {
                "success": True,
                "saved_count": saved_count,
                "errors": errors
            }

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error saving to database: {e}")
            return {
                "success": False,
                "error": str(e),
                "saved_count": 0,
                "errors": []
            }

    def _map_to_park_model(self, record: Dict[str, Any]) -> Park:
        """Map Excel record to Park model using dynamic column detection"""
        # Create a temporary DataFrame to use _find_column method
        temp_df = pd.DataFrame([record])

        return Park(
            extraction_date=self._safe_date(record.get(
                self._find_column(temp_df, ['Extraction Date', 'extraction']) or 'Extraction Date_Date d \'extraction')),
            dot_id=record.get('dot_id'),
            actel_code=record.get(
                self._find_column(temp_df, ['Actel Code', 'actel']) or 'Actel Code_Code d\'actel'),
            customer_l1_code=record.get(
                self._find_column(temp_df, ['Code Customer L1', 'level 1']) or 'Code Customer L1_Code Catégorie level 1'),
            customer_l1_description=record.get(
                self._find_column(temp_df, ['Description Customer L1', 'level 1']) or 'Description Customer L1_Nom du Catégorie level 1'),
            customer_l2_code=record.get(
                self._find_column(temp_df, ['Code Customer L2', 'level 2']) or 'Code Customer L2_Code Catégorie level 2'),
            customer_l2_description=record.get(
                self._find_column(temp_df, ['Description Customer L2', 'level 2']) or 'Description Customer L2_Nom du Catégorie level 2'),
            customer_l3_code=record.get(
                self._find_column(temp_df, ['Code Customer L3', 'level 3']) or 'Code Customer L3_Code Catégorie level 3'),
            customer_l3_description=record.get(
                self._find_column(temp_df, ['Description Customer L3', 'level 3']) or 'Description Customer L3_Nom du Catégorie level 3'),
            telecom_type=record.get(
                self._find_column(temp_df, ['Telecom type', 'SERVICE']) or 'Telecom type_SERVICE / PRODUIT'),
            offer_type=record.get(
                self._find_column(temp_df, ['Offer Type', 'offre']) or 'Offer Type_Type d\'offre'),
            offer_name=record.get(
                self._find_column(temp_df, ['Offer name', 'offre']) or 'Offer name_Nom de l\'offre'),
            rental_fees=self._safe_float(record.get(
                self._find_column(temp_df, ['Rental Fees', 'abonnement']) or 'Rental Fees_Frais d\'abonnement')),
            customer_code=record.get(
                self._find_column(temp_df, ['Customer code', 'NCLI']) or 'Customer code_NCLI'),
            service_number=record.get(
                self._find_column(temp_df, ['Service number', 'ND']) or 'Service number_ND'),
            related_service_number=record.get(
                self._find_column(temp_df, ['Related Service Number', 'correspondant']) or 'Related Service Number_Numero de service correspondant'),
            username=record.get(
                self._find_column(temp_df, ['USERNAME', 'utilisateur']) or 'USERNAME_Nom d\'utilisateur'),
            subscriber_status=record.get(
                self._find_column(temp_df, ['Subscriber status', 'abonne']) or 'Subscriber status_Status de l\'abonne'),
            status_date=self._safe_date(
                record.get(self._find_column(temp_df, ['Status date', 'statut']) or 'Status date_Date du statut')),
            creation_date=self._safe_date(
                record.get(self._find_column(temp_df, ['Creation Date', 'creation']) or 'Creation Date_Date de creation')),
            active_date=self._safe_date(record.get(
                self._find_column(temp_df, ['Active Date', 'activation']) or 'Active Date_Date d\'activation')),
            csr_name=record.get(
                self._find_column(temp_df, ['CSR Name', 'CSR']) or 'CSR Name_Nom CSR'),
            department_name=record.get(
                self._find_column(temp_df, ['Department Name', 'département']) or 'Department Name_Nom de département1'),
            state=record.get(
                self._find_column(temp_df, ['State', 'Wilaya']) or 'State_Wilaya'),
            area=record.get(
                self._find_column(temp_df, ['Area', 'Daira']) or 'Area_Daira'),
            town=record.get(
                self._find_column(temp_df, ['Town', 'Commune']) or 'Town_Commune'),
            grid=record.get(
                self._find_column(temp_df, ['Grid', 'Quartier']) or 'Grid_Quartier'),
            street=record.get(
                self._find_column(temp_df, ['Street', 'Voie']) or 'Street_Voie'),
            street_number=record.get(
                self._find_column(temp_df, ['Street Number', 'Voie']) or 'Street Number_Numero De Voie'),
            building_no=record.get(
                self._find_column(temp_df, ['Building No', 'Batiment']) or 'Building No._Batiment'),
            unit=record.get(
                self._find_column(temp_df, ['Unit', 'Escalier']) or 'Unit_Escalier'),
            floor=record.get(
                self._find_column(temp_df, ['Floor', 'Etage']) or 'Floor_Etage'),
            house_no=record.get(
                self._find_column(temp_df, ['House No', 'maison']) or 'House No._Numero de maison'),
            additional_address_info=record.get(
                self._find_column(temp_df, ['Additional Address Information', 'adresse']) or 'Additional Address Information_Complément d\'adresse'),
            customer_full_name=record.get(
                self._find_column(temp_df, ['Customer full name', 'PRENOM']) or 'Customer full name_NOM ET PRENOM'),
            province=record.get(
                self._find_column(temp_df, ['Province', 'Wilaya']) or 'Province_Wilaya'),
            district=record.get(
                self._find_column(temp_df, ['District', 'Daira']) or 'District_Daira'),
            city=record.get(
                self._find_column(temp_df, ['City', 'Commune']) or 'City_Commune'),
            postal_code=record.get(
                self._find_column(temp_df, ['Postal Code', 'postal']) or 'Postal Code_Code postal'),
            expiry_date=self._safe_date(record.get(
                self._find_column(temp_df, ['Expiry Date', 'expiration']) or 'Expiry Date_Date d\'expiration')),
            iccid=record.get(
                self._find_column(temp_df, ['ICCID', 'SIM']) or 'ICCID_N° SIM'),
            imsi=record.get(
                self._find_column(temp_df, ['IMSI', 'IMSI']) or 'IMSI_IMSI'),
            contact_number=record.get(
                self._find_column(temp_df, ['Contact number', 'contact']) or 'Contact number_Numéro de contact')
        )

    def _safe_date(self, value) -> Optional[date]:
        """Safely convert value to date"""
        if pd.isna(value) or value is None:
            return None
        try:
            if isinstance(value, str):
                # Try standard ISO format first
                try:
                    return pd.to_datetime(value, format='%Y-%m-%d', errors='raise').date()
                except:
                    # Fallback to flexible parsing
                    return pd.to_datetime(value, dayfirst=False, errors='raise').date()
            elif hasattr(value, 'date'):
                return value.date()
            return None
        except:
            return None

    def _safe_float(self, value) -> Optional[float]:
        """Safely convert value to float"""
        if pd.isna(value) or value is None:
            return None
        try:
            return float(value)
        except:
            return None
