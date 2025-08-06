import json
import os
import networkx as nx
import pandas as pd
from openai import OpenAI
from .models import ChatSession, ChatMessage, BuyerCompany, PolicyViolation
import re
from langchain_chroma import Chroma
# from langchain_community.embeddings import SentenceTransformerEmbeddings
from langchain.embeddings import SentenceTransformerEmbeddings
class UtilsManager:
    def __init__(self):
        # Initialize OpenRouter client
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.getenv("OPENROUTER_API_KEY")
        )
        
        # Initialize embeddings and database
        self.embeddings = SentenceTransformerEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
        self.db = Chroma(persist_directory="./chatbot/taiwan_db", embedding_function=self.embeddings)
        
        # Define case graphs
        self.legal_rights_graph = {
            "case_type": "Legal Rights Inquiry",
            "nodes": {
                "start": {
                    "text": "Collect basic information about the legal rights inquiry."
                },
                "rag_response": {
                    "text": "Provide comprehensive legal information using RAG approach based on the user's query."
                }
            },
            "edges": [
                ["start", "rag_response"]
            ]
        }

        self.lender_harassment_graph = {
            "case_type": "Lender Harassment",
            "nodes": {
                "start": {
                    "text": "Collect basic information about the lender harassment situation."
                },
                "document_interactions": {
                    "text": "Document all interactions with the lender, including dates, times, and what was said."
                },
                "check_loan_terms": {
                    "text": "Review the loan agreement terms and identify any violations by the lender."
                },
                "gather_evidence": {
                    "text": "Collect evidence such as threatening messages, call logs, or witness statements."
                },
                "legal_options": {
                    "text": "Explore legal options such as filing a complaint with regulatory authorities."
                },
                "safety_plan": {
                    "text": "Develop a safety plan if the harassment involves threats or intimidation."
                },
                "generate_report": {
                    "text": "Generate a comprehensive report of the harassment case."
                }
            },
            "edges": [
                ["start", "document_interactions"],
                ["document_interactions", "check_loan_terms"],
                ["check_loan_terms", "gather_evidence"],
                ["gather_evidence", "legal_options"],
                ["legal_options", "safety_plan"],
                ["safety_plan", "generate_report"]
            ]
        }

        self.employer_exploitation_graph = {
            "case_type": "Employer Exploitation",
            "nodes": {
                "start": {
                    "text": "Begin by asking the client to describe their problem. Don't ask many questions; let the client tell their story first."
                },
                "collect_basic_info": {
                    "text": "Collect basic information: What is the name of the factory? What type of goods does it produce? What is the factory address? What his task (job) in the factory?"
                },
                "collect_brand_info": {
                    "text": "Collect information about the brand/buyer companies if the user know: Do you know who are the companies that your factory supply to? If you don't know don't wort."
                },

                "ask_recruitment_agency": {
                    "text": "Ask for the name of the recruitment agency and any brokers involved."
                },
                "ask_for_contract": {
                    "text": "Request a copy or detailed description of their employment contract."
                },
                "ask_for_proof": {
                    "text": "Ask for evidence of exploitation (photos, messages, pay slips, etc.)."
                },
                "generate_report": {
                    "text": "Automatically generate policy violation report based on collected evidence"
                }
            },
            "edges": [
                ["start", "collect_basic_info"],
                ["collect_basic_info", "collect_brand_info"],
                ["collect_brand_info", "ask_recruitment_agency"],
                ["ask_recruitment_agency", "ask_for_contract"],
                ["ask_for_contract", "ask_for_proof"],
                ["ask_for_proof", "generate_report"]
            ]
        }

        self.excessive_interest_graph = {
            "case_type": "Excessive Interest Rate",
            "nodes": {
                "start": {
                    "text": "Collect basic information about the loan and interest rate concerns."
                },
                "review_loan_agreement": {
                    "text": "Review the loan agreement to identify interest rates, fees, and terms."
                },
                "calculate_effective_rate": {
                    "text": "Calculate the effective interest rate including all fees and charges."
                },
                "check_legal_limits": {
                    "text": "Check legal interest rate limits in the relevant jurisdiction."
                },
                "document_communications": {
                    "text": "Document all communications with the lender regarding the loan."
                },
                "explore_refinancing": {
                    "text": "Explore refinancing options or debt consolidation possibilities."
                },
                "generate_report": {
                    "text": "Generate a comprehensive report of the excessive interest case."
                }
            },
            "edges": [
                ["start", "review_loan_agreement"],
                ["review_loan_agreement", "calculate_effective_rate"],
                ["calculate_effective_rate", "check_legal_limits"],
                ["check_legal_limits", "document_communications"],
                ["document_communications", "explore_refinancing"],
                ["explore_refinancing", "generate_report"]
            ]
        }

        self.agency_harassment_graph = {
            "case_type": "Recruitment Agency Harassment",
            "nodes": {
                "start": {
                    "text": "Collect basic information about the recruitment agency and harassment situation."
                },
                "document_interactions": {
                    "text": "Document all interactions with the agency, including dates, times, and what was said."
                },
                "check_agency_status": {
                    "text": "Check if the recruitment agency is legally registered and licensed."
                },
                "assess_threats": {
                    "text": "Assess the nature and severity of threats or harassment from the agency."
                },
                "report_authorities": {
                    "text": "Discuss options for reporting the agency to relevant authorities."
                },
                "refer_lawyer": {
                    "text": "Provide information on seeking legal assistance for the harassment."
                },
                "ensure_protection": {
                    "text": "Discuss measures to ensure personal safety and protection."
                },
                "generate_report": {
                    "text": "Generate a comprehensive report of the agency harassment case."
                }
            },
            "edges": [
                ["start", "document_interactions"],
                ["document_interactions", "check_agency_status"],
                ["check_agency_status", "assess_threats"],
                ["assess_threats", "report_authorities"],
                ["report_authorities", "refer_lawyer"],
                ["refer_lawyer", "ensure_protection"],
                ["ensure_protection", "generate_report"]
            ]
        }

    def relevant_context(self, user_input):
        """Get relevant context from the database based on user input.
        
        Args:
            user_input (str): The user's query
            
        Returns:
            object: The retrieved context
        """
        # Modify the filter based on the origin and destination
        retriever_vectordb = self.db.as_retriever(
            search_kwargs={
                'k': 1
            }
        )

        context = retriever_vectordb.invoke(user_input)

        return context

    def create_prompt_template(self, user_input, context, chat_history):
        """Create a prompt template for the AI based on user input, context, and chat history.
        
        Args:
            user_input (str): The user's query
            context (object): The retrieved context
            chat_history (list): List of message dictionaries
            
        Returns:
            str: The prompt template
        """
        template = f"""
        Context: {str(context)}
        Chat History: {str(chat_history)}

        The input query is: \"{user_input}\".

        Based on the user's query, only apply the guidelines that are relevant to their specific situation:

        FINANCIAL/DEBT GUIDELINES (only use if the query is about debt, loans, financial problems, or lender issues):
        - Encourage open communication and negotiation with lenders. Suggest steps such as:
            1. Requesting an extension of payment deadlines.
            2. Asking for temporary reduced payment amounts.
            3. Exploring loan restructuring options.
        - Recommend seeking professional financial counseling from NGOs or social welfare organizations that specialize in supporting domestic helpers.

        EMPLOYMENT/LEGAL GUIDELINES (only use if the query is about employment rights, labor laws, or workplace issues):
        - Prioritize the stability of the client's employment and their compliance with Taiwan's employment and immigration laws.
        - Ensure the response is supportive, compassionate, and emphasizes the client's well-being while maintaining their legal and contractual obligations.

        UNIVERSAL RESTRICTIONS (always apply):
        When responding, ensure that you do not:
        - Advise keeping secrets from employers, especially concerning money lending or personal financial matters.
        - Provide guidance that contradicts transparency and ethical practices in a workplace environment.
        - Suggest extra work or activities that could jeopardize the client's employment status.
        - Recommend any illegal or unauthorized employment as a way to pay off debts or loans.
        - Include any bold formatting in the text provided.

        UNIVERSAL GUIDANCE (always apply):
        - Ask for clarification if needed.
        - Provide a complete, concise, and easy-to-understand response.
        - Respond in a compassionate and human-like format without repeating yourself.
        - Avoid mentioning anything about the context to the user.
        """
        return template

    def refine_user_query_for_rag(self, chat_history, current_query, model="google/gemma-3n-e4b-it:free"):
        """
        Refine and concatenate user queries from chat history to create a comprehensive search query for RAG.
        
        Args:
            chat_history (list): List of message dictionaries with 'role' and 'content'
            current_query (str): The current user query
            model (str): The model to use for query refinement
            
        Returns:
            str: Refined comprehensive query for RAG retrieval
        """
        # Extract only user messages from chat history
        user_messages = [msg["content"] for msg in chat_history if msg["role"] == "user"]
        
        # Add current query if not already in history
        if current_query and current_query not in user_messages:
            user_messages.append(current_query)
        
        # If only one query, return it as is
        if len(user_messages) <= 1:
            return current_query
        
        # Create a prompt to refine multiple user queries into one comprehensive query
        user_queries_text = "\n".join([f"Query {i+1}: {query}" for i, query in enumerate(user_messages)])
        
        prompt = f"""
You are a query refinement specialist. The user has asked multiple related questions in a conversation about legal rights and labor law. Your task is to combine and refine these queries into one comprehensive search query that captures the complete intent and context.

User's queries in chronological order:
{user_queries_text}

Create a single, comprehensive search query that:
1. Combines the main topics and concepts from all queries
2. Maintains the specific legal context and details mentioned
3. Removes redundancy while preserving important details
4. Is optimized for retrieving relevant legal documents and information
5. Focuses on the core legal question or issue being asked

Return only the refined comprehensive query, nothing else.
"""
        
        messages = [{"role": "user", "content": prompt}]
        completion = self.client.chat.completions.create(
            model=model,
            messages=messages
        )
        
        refined_query = completion.choices[0].message.content.strip()
        print(f"Original queries: {user_messages}")
        print(f"Refined query: {refined_query}")
        
        return refined_query

    def respond_based_on_the_context_agent(self, user_input, chat_history, model="google/gemma-3n-e4b-it:free"):
        """
        Generate a response based on the context retrieved from the database.
        
        Args:
            user_input (str): The user's query
            chat_history (list): List of message dictionaries
            model (str): The model to use for the response
            
        Returns:
            str: The generated response
        """
        # Refine the query by combining chat history context
        refined_query = self.refine_user_query_for_rag(chat_history, user_input, model)
        
        # Use the refined query for context retrieval
        context = self.relevant_context(refined_query)
        print("Refined Query: ", refined_query)
        print("Context: ", context)
        
        # Create prompt template using original user input but with refined context
        input_text = self.create_prompt_template(user_input, context, chat_history)   
        temp_messages=[{"role": "user", "content": input_text}]
        messages = temp_messages
        
        completion = self.client.chat.completions.create(
            model=model,
            messages=messages
        )
        return completion.choices[0].message.content


    # Helper functions
    def query_ollama(self, messages, model="google/gemma-3n-e4b-it:free"):
        """
        Query the OpenRouter API with the given messages and model.
        
        Args:
            messages (list): List of message dictionaries with 'role' and 'content'
            model (str): The model to use for the query
            
        Returns:
            str: The content of the response message
        """
        completion = self.client.chat.completions.create(
            model=model,
            messages=messages
        )
        return completion.choices[0].message.content

    def load_case_graph(self, data):
        """
        Load a case graph from the given data.
        
        Args:
            data (dict): Dictionary containing case graph data
            
        Returns:
            tuple: (case_type, graph)
        """
        G = nx.DiGraph()
        for node_id, info in data["nodes"].items():
            G.add_node(node_id, **info)
        for src, dst in data["edges"]:
            G.add_edge(src, dst)
        return data["case_type"], G

    def identify_case_type(self, user_input):
        """
        Identify the type of legal case based on user input.
        
        Args:
            user_input (str): The user's description of their problem
            
        Returns:
            str: The identified case type
        """
        prompt = f"""
        You are a legal assistant. Based on the following user information, identify the type of legal case they are dealing with:

        - Legal Rights Inquiry (for general legal questions, rights information, labor law questions, legal advice)
        - Lender Harassment
        - Employer Exploitation
        - Excessive Interest Rate
        - Recruitment Agency Harassment 

        Be concise and return only the case type as named above.

        Problem: {user_input}
        """
        messages = [{"role": "user", "content": prompt}]
        response = self.query_ollama(messages)
        case_type = response.strip()
        print("Case_Type: ", case_type)
        return case_type

    def extract_factory_name(self, history):
        """
        Extract the factory name from conversation history.
        
        Args:
            history (list): List of message dictionaries
            
        Returns:
            str: The extracted factory name
        """
        prompt = f"""
        Based on the provided history, extract the factory name mentioned. Only return the factory name, nothing else.

        History: {str(history)}
        """
        messages = [{"role": "user", "content": prompt}]
        response = self.query_ollama(messages)
        factory_name = response.strip()
        return factory_name

    def get_graph_for_case(self, case_type):
        """
        Get the appropriate graph for the given case type.
        
        Args:
            case_type (str): The type of case
            
        Returns:
            tuple or None: (case_type, graph) or None if case type not found
        """
        if case_type.lower() == "legal rights inquiry":
            return self.load_case_graph(self.legal_rights_graph)
        
        elif case_type.lower() == "lender harassment":
            return self.load_case_graph(self.lender_harassment_graph)
        
        elif case_type.lower() == "employer exploitation":
            return self.load_case_graph(self.employer_exploitation_graph)
        
        elif case_type.lower() == "excessive interest rate":
            return self.load_case_graph(self.excessive_interest_graph)
        
        elif case_type.lower() == "recruitment agency harassment":
            return self.load_case_graph(self.agency_harassment_graph)
        
        else:
            return None

    def check_navigation_to_next_state(self, history, current_node, G, model="google/gemma-3n-e4b-it:free"):
        """
        Check if the conversation should navigate to the next state.
        
        Args:
            history (list): List of message dictionaries
            current_node (str): The current node in the conversation graph
            G (nx.DiGraph): The conversation graph
            model (str): The model to use for the query
            
        Returns:
            str: "Yes" or "No" indicating whether to navigate to the next state
        """
        current_text = G.nodes[current_node]["text"]

        recent_user_msg = history[-1]['content'] if history else ''
        recent_bot_msg = next((msg["content"] for msg in reversed(history) if msg["role"] == "assistant"), "")

        prompt = f"""
You are a conversation state evaluator helping a legal assistant chatbot.

Your task is to determine whether the user has provided sufficient information to complete the current conversation step and proceed to the next one.

📌 Current step requirements:
{current_text}

💬 Most recent bot message:
{recent_bot_msg}

🗣️ Most recent user reply:
{recent_user_msg}

Evaluation criteria:
- Has the user provided relevant information that addresses the current step's requirements?
- Is the information sufficient to move forward, even if not complete?
- Does the user's response show they understand what was asked?

If the user's reply **directly addresses** the current step's requirements with relevant information, return exactly 'Yes'.
If the user's reply is off-topic, unclear, or doesn't address the current step, return exactly 'No'.

🔒 Only return 'Yes' or 'No'. Do not include explanations or anything else.
"""

        messages = [{"role": "user", "content": prompt}]
        completion = self.client.chat.completions.create(
            model=model,
            messages=messages
        )
        result = completion.choices[0].message.content.strip()

        print("Debug: check_navigation_to_next_state() raw response →", result)

        print(f"\n=== Checking navigation from [{current_node}] ===")
        print(f"Current step: {current_text}")
        print(f"Last user input: {history[-1]['content'] if history else 'None'}")
        print("=== Raw model response ===")
        print(result)

        # More robust checking for "Yes" response
        if result.lower().startswith("yes") or result.lower() == "yes":
            return "Yes"
        else:
            return "No"

    def build_prompt(self, case_type, current_node, G, history, user_query):
        """
        Build a prompt for the AI based on the current conversation state.
        
        Args:
            case_type (str): The type of case
            current_node (str): The current node in the conversation graph
            G (nx.DiGraph): The conversation graph
            history (list): List of message dictionaries
            user_query (str): The user's latest message
            
        Returns:
            str: The prompt for the AI
        """
        current_info = G.nodes[current_node]["text"]
        
        # If user_query is empty, this is for generating next step questions
        if not user_query.strip():
            prompt = f"""
You are a helpful legal assistant chatbot. Based on the current conversation step, ask the user for the required information.

Current step requirements: {current_info}

Chat history (to avoid repeating questions): {history}

Generate a clear, concise question to gather the information needed for this step. Be polite and professional.
Don't repeat questions that have already been asked or information that has already been provided.
"""
        else:
            # This is for responding to user input
            prompt = f"""
You are a helpful legal assistant chatbot. The user has provided information related to the current conversation step.

Current step requirements: {current_info}

Chat history: {history}

User's message: {user_query}

Acknowledge the user's input appropriately and professionally. If the information is helpful, thank them. If you need clarification, ask politely.
Don't repeat what the user said. Keep your response concise and move the conversation forward naturally.
"""
        
        return prompt


    def search_buyer_company_from_factory(self, factory_name, match_type='both'):
        """
        Search for buyer companies associated with a factory.
        
        Args:
            factory_name (str): The name of the factory
            match_type (str): 'exact', 'partial', or 'both' (combines exact and partial)
            similarity_threshold (float): Threshold for fuzzy matching (0.0 to 1.0)
            
        Returns:
            list: List of buyer company names
        """
        try:
            supplier_df = pd.read_csv("./chatbot/data/Taiwan Supplier List.xlsx - Full List.csv")
            supplier_df.columns = supplier_df.columns.str.strip()
            
            all_buyers = set()  # Use set to avoid duplicates
            
            if match_type == 'exact':
                # Exact matching (case-insensitive) with punctuation normalization
                normalized_factory = factory_name.lower().strip().rstrip('.')
                matched = supplier_df[
                    (supplier_df["Taiwan Company"].str.lower().str.strip().str.rstrip('.') == normalized_factory) |
                    (supplier_df["Taiwan Company"].str.lower() == factory_name.lower())
                ]
                buyers = matched["Customer Company"].dropna().unique().tolist()
                all_buyers.update(buyers)
                
            elif match_type == 'partial':
                # Partial matching (contains)
                matched = supplier_df[supplier_df["Taiwan Company"].str.contains(factory_name, case=False, na=False)]
                buyers = matched["Customer Company"].dropna().unique().tolist()
                all_buyers.update(buyers)
                
            elif match_type == 'both':
                # Combine exact and partial matching
                
                # Exact matching with punctuation normalization
                normalized_factory = factory_name.lower().strip().rstrip('.')
                exact_matched = supplier_df[
                    (supplier_df["Taiwan Company"].str.lower().str.strip().str.rstrip('.') == normalized_factory) |
                    (supplier_df["Taiwan Company"].str.lower() == factory_name.lower())
                ]
                all_buyers.update(exact_matched["Customer Company"].dropna().unique().tolist())
                
                # Partial matching
                partial_matched = supplier_df[supplier_df["Taiwan Company"].str.contains(factory_name, case=False, na=False)]
                all_buyers.update(partial_matched["Customer Company"].dropna().unique().tolist())
            
            return list(all_buyers)
            
        except Exception as e:
            print(f"Error searching buyer companies: {e}")
            return []

    def extract_incident(self, chat_history, model="google/gemma-3n-e4b-it:free"):
        prompt = f"""
Extract a summary that includes the incidents that the user mentioned based on the given chat history.

Make sure that includes the key points of the violation incidents without repetition.

Chat History: {str(chat_history)}

"""
        messages = [{"role": "user", "content": prompt}]
        completion = self.client.chat.completions.create(
            model=model,
            messages=messages
        )
        result = completion.choices[0].message.content.strip().lower()
        return result


    def get_company_policy_report(self, company_name, incident_description, model="google/gemma-3n-e4b-it:free"):
        """
        Enhanced version that matches violations to incidents with full reference details.
        """
        try:
            # Load the first policy CSV
            policies_df = pd.read_csv("./chatbot/data/List of Company - Data List.xlsx - (1) 1000 Company List.csv")
            policies_df.columns = policies_df.columns.str.strip()

            # Load the additional policy CSV
            extra_policy_df = pd.read_csv("./chatbot/data/Companies_Policies.csv")
            extra_policy_df.columns = extra_policy_df.columns.str.strip()

            # Match company name in both files
            company_row = policies_df[policies_df["Name of Company"].str.lower() == company_name.lower()]
            extra_row = extra_policy_df[extra_policy_df["Name of Company"].str.lower() == company_name.lower()]

            if company_row.empty and extra_row.empty:
                return json.dumps({
                    "error": f"No policy information found for company: {company_name}"
                })

            # Extract policy text and build comprehensive policy mapping
            policy_text = ""
            policy_mapping = {}
            
            # Define policy fields with their corresponding reference columns
            policy_fields = [
                {
                    "field": "Does the company prohibit recruitment fees to workers? Paste only relevant sentences.",
                    "doc_name": "Name of Reference Document 1",
                    "doc_link": "Reference Document Link",
                    "category": "Recruitment Fees"
                },
                {
                    "field": "Reference to fee repayment if workers are found to have paid (up to three sentences)",
                    "doc_name": "Name of Reference Document 1",
                    "doc_link": "If yes, provide link 1",
                    "category": "Fee Repayment"
                },
                {
                    "field": "Reference to Confiscation of travel/ identity document. If yes, mention up to three sentences.",
                    "doc_name": "Name of Reference Document 2",
                    "doc_link": "If yes, provide link 2",
                    "category": "Document Confiscation"
                }
            ]

            for policy_info in policy_fields:
                if not company_row.empty:
                    value = company_row.iloc[0].get(policy_info["field"])
                    doc_name = company_row.iloc[0].get(policy_info["doc_name"])
                    doc_link = company_row.iloc[0].get(policy_info["doc_link"])
                    
                    if pd.notna(value) and value.strip():
                        # Add full policy content to text
                        policy_text += f"[{policy_info['category']}] {policy_info['field']}: {value}\n\n"
                        
                        # Store comprehensive mapping
                        policy_mapping[policy_info["category"]] = {
                            "field_name": policy_info["field"],
                            "policy_content": value.strip(),
                            "document_name": doc_name.strip() if pd.notna(doc_name) else "Unknown Document",
                            "document_url": doc_link.strip() if pd.notna(doc_link) else "No URL available"
                        }

            # Handle extra policy fields with their references
            extra_fields = [
                {"field": "Heat Stress", "reference": "Heat Stress Reference", "category": "Heat Stress"},
                {"field": "Health Care", "reference": "Health Care Reference", "category": "Health Care"},
                {"field": "Wages and OverTime", "reference": "Wages Reference", "category": "Wages and Overtime"}
            ]
            
            for field_info in extra_fields:
                if not extra_row.empty:
                    value = extra_row.iloc[0].get(field_info["field"])
                    reference = extra_row.iloc[0].get(field_info["reference"])
                    
                    if pd.notna(value) and value.strip():
                        policy_text += f"[{field_info['category']}] {field_info['field']} Policy: {value}\n\n"
                        
                        # Parse reference to extract document name and page number
                        doc_name = "Company Policy Document"
                        doc_url = "Not available"
                        
                        if pd.notna(reference) and reference.strip():
                            # Extract document name and page info from reference
                            # Format appears to be: "document_name.pdf page no.:XX"
                            ref_parts = reference.strip().split(" page no.:")
                            if len(ref_parts) >= 1:
                                doc_name = ref_parts[0].strip()
                                if len(ref_parts) > 1:
                                    doc_name += f" (Page {ref_parts[1].strip()})"
                        
                        policy_mapping[field_info["category"]] = {
                            "field_name": f"{field_info['field']} Policy",
                            "policy_content": value.strip(),
                            "document_name": doc_name,
                            "document_url": doc_url,
                            "reference_info": reference.strip() if pd.notna(reference) else "No reference available"
                        }

            # Enhanced prompt for better incident-policy matching with violation consolidation
            prompt = f"""
You are a legal analyst assessing corporate compliance with labor policies.

You will be given:
1. A worker's incident report.
2. The company's official policy text with categories in brackets.

Your task is to:
- Summarize the complaint in one sentence.
- Extract and list **only** the specific incidents reported by the worker as bullet points.
- Identify policy violations ONLY when there is a direct and clear connection between the reported incidents and the policy categories.
- For each policy violation, list all related incidents and provide one comprehensive violation description.

CRITICAL RULES:
1. Do NOT create violations for policy categories that are not directly related to the reported incidents.
2. Do NOT make assumptions or inferences beyond what is explicitly stated in the incident report.
3. Do NOT create separate violations for incidents that fall under the same policy category. Group them together.
4. Only identify violations where the incidents clearly and directly violate the specific policy content.

Respond strictly in the following JSON format:

{{
  "complaint_summary": "One sentence summary of the worker's complaint.",
  "incidents": [
    "List key details of the incident as bullet points"
  ],
  "policy_violations": [
    {{
      "policy_category": "The policy category from brackets (e.g., 'Recruitment Fees', 'Document Confiscation', 'Wages and Overtime')",
      "related_incidents": [
        "List of incidents from the incidents list that relate to this policy violation"
      ],
      "violation_description": "Comprehensive description of how the related incidents collectively violate this policy"
    }}
  ]
}}

Do not include any commentary or explanations outside the JSON structure.

Incident Report:
{incident_description}

Company Policy Documents:
{policy_text}
"""

            # Query model
            messages = [{"role": "user", "content": prompt}]
            response = self.query_ollama(messages, model=model)

            # Strip triple backticks or markdown formatting from model output
            cleaned_response = re.sub(r"^```(?:json)?|```$", "", response.strip(), flags=re.MULTILINE).strip()

            # Attempt to parse response into JSON
            try:
                parsed = json.loads(cleaned_response)
                
                # Enhance policy violations with full reference details
                if "policy_violations" in parsed:
                    for i, violation in enumerate(parsed["policy_violations"]):
                        if isinstance(violation, dict) and "policy_category" in violation:
                            category = violation["policy_category"]
                            if category in policy_mapping:
                                # Add comprehensive reference information
                                ref_info = {
                                    "policy_content": policy_mapping[category]["policy_content"],
                                    "document_name": policy_mapping[category]["document_name"],
                                    "document_url": policy_mapping[category]["document_url"],
                                    "field_name": policy_mapping[category]["field_name"]
                                }
                                
                                # Add reference info if available (for extra fields)
                                if "reference_info" in policy_mapping[category]:
                                    ref_info["reference_info"] = policy_mapping[category]["reference_info"]
                                
                                parsed["policy_violations"][i]["reference"] = ref_info
                            else:
                                # Try partial matching if exact category not found
                                for mapped_category, mapping_info in policy_mapping.items():
                                    if any(word.lower() in mapped_category.lower() for word in category.lower().split()):
                                        parsed["policy_violations"][i]["reference"] = {
                                            "policy_content": mapping_info["policy_content"],
                                            "document_name": mapping_info["document_name"],
                                            "document_url": mapping_info["document_url"],
                                            "field_name": mapping_info["field_name"]
                                        }
                                        if "reference_info" in mapping_info:
                                            parsed["policy_violations"][i]["reference"]["reference_info"] = mapping_info["reference_info"]
                                        break
                
                return json.dumps(parsed, indent=2, ensure_ascii=False)
                
            except json.JSONDecodeError:
                return json.dumps({
                    "error": "Model did not return valid JSON.",
                    "raw_response": response.strip(),
                    "available_policies": policy_mapping
                }, indent=2, ensure_ascii=False)

        except Exception as e:
            return json.dumps({
                "error": f"Unable to generate policy report for {company_name}: {str(e)}"
            }, indent=2, ensure_ascii=False)

# New functions for language and location identification
    def identify_language(self, user_message, model="google/gemma-3n-e4b-it:free"):
        """
        Identify the language used in the user's message.
        
        Args:
            user_message (str): The user's message
            model (str): The model to use for the query
            
        Returns:
            str: The identified language
        """
        prompt = f"""
        You are a language identification agent. Based on the following user message, identify the language being used.
        Return only the language name in English (e.g., "English", "Spanish", "Chinese", etc.).If no Language is mentioned, return "None".
        Do not include any additional text or explanations.

        User message: "{user_message}"
        """
        
        messages = [{"role": "user", "content": prompt}]
        response = self.query_ollama(messages, model=model)
        print("Language: ", response)
        return response.strip()

    def extract_location(self, user_message, model="google/gemma-3n-e4b-it:free"):
        """
        Extract location information from the user's message.
        
        Args:
            user_message (str): The user's message
            model (str): The model to use for the query
            
        Returns:
            str or None: The extracted location or None if no location found
        """
        prompt = f"""
        You are a location extraction agent. Based on the following user message, extract any location information mentioned (country, city, region, etc.).
        Return only the location name. If no location is mentioned, return "None".
        Do not include any additional text or explanations.

        User message: "{user_message}"
        """
        
        messages = [{"role": "user", "content": prompt}]
        response = self.query_ollama(messages, model=model)
        result = response.strip()
        print("Location: ", result)
        return None if result.lower() == "none" else result

    def extract_gender(self, user_message, model="google/gemma-3n-e4b-it:free"):
        """
        Extract gender information from the user's message.
        
        Args:
            user_message (str): The user's message
            model (str): The model to use for the query
            
        Returns:
            str or None: The extracted gender or None if no gender found
        """
        prompt = f"""
        You are a gender extraction agent. Based on the following user message, extract any gender information mentioned.
        Return only the gender (e.g., "Male", "Female", "Non-binary", etc.). If no gender is mentioned, return "None".
        Do not include any additional text or explanations.

        User message: "{user_message}"
        """
        
        messages = [{"role": "user", "content": prompt}]
        response = self.query_ollama(messages, model=model)
        result = response.strip()
        print("Gender: ", result)
        return None if result.lower() == "none" else result

    def extract_nationality(self, user_message, model="google/gemma-3n-e4b-it:free"):
        """
        Extract nationality information from the user's message.
        
        Args:
            user_message (str): The user's message
            model (str): The model to use for the query
            
        Returns:
            str or None: The extracted nationality or None if no nationality found
        """
        prompt = f"""
        You are a nationality extraction agent. Based on the following user message, extract any nationality information mentioned.
        Return only the nationality name (e.g., "Indonesian", "Thai", "Vietnamese", etc.). If no nationality is mentioned, return "None".
        Do not include any additional text or explanations.

        User message: "{user_message}"
        """
        
        messages = [{"role": "user", "content": prompt}]
        response = self.query_ollama(messages, model=model)
        result = response.strip()
        print("Nationality: ", result)
        return None if result.lower() == "none" else result


    def extract_industrial_sector(self, user_message, model="google/gemma-3n-e4b-it:free"):
        """
        Extract industrial sector information from the user's message.
        
        Args:
            user_message (str): The user's message
            model (str): The model to use for the query
            
        Returns:
            str or None: The extracted industrial sector or None if no industrial sector found
        """
        prompt = f"""
        You are an industrial sector extraction agent. Based on the following user message, extract any industrial sector or factory type information mentioned.
        Return only the industrial sector name (e.g., "Electronics", "Textiles", "Food Processing", "Automotive", etc.). If no industrial sector is mentioned, return "None".
        Do not include any additional text or explanations.

        User message: "{user_message}"
        """
        
        messages = [{"role": "user", "content": prompt}]
        response = self.query_ollama(messages, model=model)
        result = response.strip()
        print("Industrial Sector: ", result)
        return None if result.lower() == "none" else result


    def translate_to_English(self, user_message, model="google/gemma-3n-e4b-it:free"):
        """
        Translate the non-English user input to English sentence.
        
        Args:
            user_message (str): The user's message
            model (str): The model to use for the query
            
        Returns:
            str or None: The translated sentence
        """
        prompt = f"Translate the following text to English: '{user_message}'. Keep the same punctuation as the orignial text. Return only the translated text, without any additional words, punctuation, or explanation."
        
        messages = [{"role": "user", "content": prompt}]
        response = self.query_ollama(messages, model=model)
        return response


    def translation_from_English(self, english_input, language, model="google/gemma-3n-e4b-it:free"):
        prompt = (
            f"Please translate the following English text to {language} as a fluent native speaker: '{english_input}'. "
            f"Ensure the translation captures the correct tone, meaning, and is idiomatically accurate. "
            f"Return only the translated text without any additional information, punctuation, or explanation."
            f"If the text provided is already in the target language, return it as it is without any further changes."
        )

        messages = [{"role": "user", "content": prompt}]
        response = self.query_ollama(messages, model=model)
        return response

